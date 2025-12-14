from seedemu.layers import Base, Routing, Ebgp, Ibgp, Ospf, PeerRelationship
from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator
import os
import sys
import networkx as nx
import re
import pickle
from typing import List, Tuple, Dict
from seedemu.layers import Base, Ebgp, Routing, Ibgp, Ospf
from seedemu.layers.Ebgp import PeerRelationship
from seedemu.core import Binding, Filter, Emulator, Service, Router, AutonomousSystem
from typing import List, Tuple, Dict
import time
import threading
import psutil
from datetime import datetime
from ipaddress import IPv4Address,IPv4Network
import random
from seedemu.services import TrafficService, TrafficServiceType
from seedemu.layers import EtcHosts
with open("assignment.pkl", "rb") as f:
    assignment = pickle.load(f)
node_prefix={}
for key,value in assignment.items():
    node_prefix[value['asn']]=value['ipv4']

def add_traffic(base, emu, stubAS, assignment_temp, num=10):
    etc_hosts = EtcHosts()
    traffic_service = TrafficService()
    for i in range(num):
        asnum1=assignment_temp[stubAS[3*i]]['asn']
        asnum2=assignment_temp[stubAS[3*i+1]]['asn']
        asnum3=assignment_temp[stubAS[3*i+2]]['asn']

        receiver1=f"iperf-receiver-{i}-1"
        receiver2=f"iperf-receiver-{i}-2"
        traffic_service.install(receiver1, TrafficServiceType.IPERF_RECEIVER, log_file="/root/iperf3_receiver.log")
        traffic_service.install(receiver2, TrafficServiceType.IPERF_RECEIVER, log_file="/root/iperf3_receiver.log")
        traffic_service.install(
            f"iperf-generator-{i}",
            TrafficServiceType.IPERF_GENERATOR,
            log_file="/root/iperf3_generator.log",
            protocol="TCP",
            duration=36000,
            rate=0
        ).addReceivers(hosts=[receiver1, receiver2])
        
        # Add hosts to AS-150

        as1 = base.getAutonomousSystem(asnum1)
        as1.createHost(f"iperf-generator-{i}").joinNetwork("net0")

        # Add hosts to AS-162
        as2 = base.getAutonomousSystem(asnum2)
        as2.createHost(f"iperf-receiver-{i}-1").joinNetwork("net0")

        # Add hosts to AS-171
        as3 = base.getAutonomousSystem(asnum3)
        as3.createHost(f"iperf-receiver-{i}-2").joinNetwork("net0")
        emu.addBinding(
            Binding(f"iperf-generator-{i}", filter=Filter(asn=asnum1, nodeName=f"iperf-generator-{i}"))
        )
        emu.addBinding(
            Binding(receiver1, filter=Filter(asn=asnum2, nodeName=receiver1))
        )
        emu.addBinding(
            Binding(receiver2, filter=Filter(asn=asnum3, nodeName=receiver2))
        )

    # Add the layers
    emu.addLayer(traffic_service)
    emu.addLayer(etc_hosts)

def get_assignment(asn,assignment=assignment):
    t=len(assignment)
    if asn not in assignment.keys():
        assignment[asn]={'asn':t+1,'ipv4':f'{(t+1) //256}.{(t+1) %256}.0.0/16'}
    return assignment
def update_topology_from_file(TOPOLOGY_DATA,max_new_asns=100):
    """
    从文件中读取数据更新拓扑
    :param max_new_asns: 允许新增的最大 AS 数量
    """
    
    db_filename = '201603modified.txt'
    
    print(f"正在分析未使用的 IXP... (最大新增 AS 限制: {max_new_asns})")

    # 2. 找出不存在于 as_as_ix_edges 中的 IXP
    # as_as_ix_edges 结构: [(as1, as2, ixp, rel), ...] -> ixp 是第3个元素 (index 2)
    used_ixps = set(edge[2] for edge in TOPOLOGY_DATA['as_as_ix_edges'])
    # 筛选未使用的 IXP
    unused_ixps = [ixp for ixp in TOPOLOGY_DATA['ixps'] if ixp not in used_ixps]
    
    if not unused_ixps:
        print("未发现未使用的 IXP，无需更新。")
        return TOPOLOGY_DATA

    # 3. 寻找未使用的 IXP 连接的 Transit AS (即变量 a)
    # 建立映射: { Transit_AS_a: [IXP_1, IXP_2, ...] }
    # 这样读取文件时，如果遇到 AS0 == Transit_AS_a，就可以只检查对应的几个 IXP
    as_to_target_ixps = {}
    
    count_mapped = 0
    for ixp in unused_ixps:
        connected_as = None
        # ix_ix_transit_edges 结构: [(ixp1, ixp2, as, 0)]
        for edge in TOPOLOGY_DATA['ix_ix_transit_edges']:
            ixp1, ixp2, asn, _ = edge
            if ixp == ixp1 or ixp == ixp2:
                # 修改点 1: 确保 asn 转换为整数
                connected_as = int(asn)
                break
        
        if connected_as is not None:
            if connected_as not in as_to_target_ixps:
                as_to_target_ixps[connected_as] = []
            as_to_target_ixps[connected_as].append(ixp)
            count_mapped += 1
    
    print(f"找到 {len(unused_ixps)} 个未使用 IXP，其中 {count_mapped} 个成功关联到 Transit AS。")
    print("正在扫描 201603modified.txt 进行匹配...")

    # 4. 扫描文件并查找匹配项 (a|X|ixp,-1)
    # 缓存已存在的 Stub AS 以避免重复添加检查
    existing_stubs = set(TOPOLOGY_DATA['stub_asns'])
    existing_transits = set(TOPOLOGY_DATA['transit_asns'])
    
    new_edges_count = 0
    added_asns_count = 0 # 修改点 2: 新增 AS 计数器

    with open(db_filename, 'r', encoding='utf-8') as f:
        for line in f:
            # 修改点 3: 检查是否达到数量限制
            if added_asns_count >= max_new_asns:
                print(f"已达到最大新增 AS 数量限制 ({max_new_asns})，停止处理。")
                break

            line = line.strip()
            # 过滤空行和注释
            if not line or line.startswith('#'):
                continue
            
            parts = line.split('|')
            if len(parts) < 3:
                continue
            
            # 获取 AS0 (即变量 a)
            try:
                as0 = int(parts[0])
            except ValueError:
                continue # 如果 AS 不是数字则跳过
            
            # 如果这一行的 AS0 是我们要找的 Transit AS 之一
            if as0 in as_to_target_ixps:
                target_ixps = as_to_target_ixps[as0]
                
                # 获取该行剩余部分 (loc,source...)
                # parts[0]是AS0, parts[1]是AS1 (即变量 X), parts[2:]是位置信息
                try:
                    as1 = int(parts[1]) # 变量 X
                except ValueError:
                    continue

                # 遍历该 AS 关心的所有未使用 IXP
                for ixp in target_ixps:
                    # 构造搜索字符串: "ixp,-1"
                    # 注意：确保 ixp 转为字符串与文件内容匹配
                    search_target = f"{ixp},-1"
                    
                    # 在剩余部分寻找匹配
                    is_match = False
                    for segment in parts[2:]:
                        if search_target in segment:
                            is_match = True
                            break
                    
                    if is_match:
                        # 5. 匹配成功，执行添加操作
                        
                        # 检查是否为新 AS
                        is_new_as = as1 not in existing_stubs and as1 not in existing_transits

                        if is_new_as:
                            # 再次检查限制 (以防同一行触发多次添加，虽然这里同一行是同一个AS1)
                            if added_asns_count >= max_new_asns:
                                break # 跳出内层循环，外层循环会在下一次迭代时捕获并break

                            TOPOLOGY_DATA['stub_asns'].append(str(as1))
                            existing_stubs.add(as1) # 更新缓存
                            added_asns_count += 1
                        
                            # 添加边 (a, X, ixp, -1) -> (as0, as1, ixp, -1)
                            new_edge = (str(as0), str(as1), ixp, '-1')
                            # 简单去重检查
                            if new_edge not in TOPOLOGY_DATA['as_as_ix_edges']:
                                TOPOLOGY_DATA['as_as_ix_edges'].append(new_edge)
                                new_edges_count += 1
                                # print(f"添加边: {new_edge}") 
                
                # 如果在内层循环触发了限制，外层也需要退出
                if added_asns_count >= max_new_asns:
                    break
    
    print(f"处理完成。新增了 {added_asns_count} 个 AS，{new_edges_count} 条 AS-AS-IX 边。")
    return TOPOLOGY_DATA

def generate_connected_pairs(nodes, extra_edges_count=0):
    """
    生成随机连接对，确保图是连通的。
    :param nodes: 节点列表
    :param extra_edges_count: 在保证连通后，额外增加多少条随机边
    """
    if len(nodes) < 2:
        return []
    elif len(nodes) == 2:
        return [tuple(sorted((nodes[0], nodes[1])))]
    
    pairs = set() # 使用集合避免重复边
    for i in range(len(nodes)):
        pair1 = tuple(sorted((nodes[i],nodes[(i + 1) % len(nodes)])))
        pairs.add(pair1)
    for i in range(len(nodes)):
        if len(pairs)<254:
            break;
        if i!= (int(i + 1+len(nodes)/2) % len(nodes)):
            pair2 = tuple(sorted((nodes[i],nodes[int(i + 1+len(nodes)/2) % len(nodes)])))
            pairs.add(pair2)
    
    # # 3. (可选) 添加额外的随机边，增加网络复杂度
    # # 如果您只需要最基本的连通，可以让 extra_edges_count = 0
    # current_edge_count = len(pairs)
    # max_edges = len(nodes) * (len(nodes) - 1) // 2 # 全连接图的边数
    
    # # 防止请求的额外边数超过最大可能的边数
    # target_count = min(current_edge_count + extra_edges_count, max_edges)
    
    # while len(pairs) < target_count:
    #     # 随机选两个不同的节点
    #     u, v = random.sample(nodes, 2)
    #     pair = tuple(sorted((u, v)))
        
    #     # 集合会自动去重，如果该边已存在则不会添加
    #     pairs.add(pair)

    return list(pairs)

class ResourceMonitor:
    def __init__(self, interval=1):
        """
        初始化资源监控器
        :param interval: 监控间隔（秒），默认1秒
        """
        self.interval = interval
        self.running = False
        self.thread = None
        # 生成以当前时间命名的日志文件（格式：YYYYMMDD_HHMMSS.log）
        self.log_filename = datetime.now().strftime("%Y%m%d_%H%M%S.log")
        # 确保日志文件目录存在（当前目录）
        self.log_path = os.path.join(os.getcwd(), self.log_filename)
        # 写入日志头部（列名）
        with open(self.log_path, 'w', encoding='utf-8') as f:
            f.write("时间,CPU使用率(%),内存占用(MB),内存使用率(%)\n")

    def _monitor(self):
        """监控逻辑（后台线程执行）"""
        while self.running:
            # 获取当前时间（精确到毫秒）
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            
            # 获取CPU使用率（interval=0.1表示采样0.1秒内的平均使用率）
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # 获取内存信息
            mem = psutil.virtual_memory()
            mem_used_mb = mem.used / (1024 **2)  # 转换为MB
            mem_percent = mem.percent
            
            # 写入日志（格式：时间,CPU%,内存MB,内存%）
            log_line = f"{current_time},{cpu_percent:.2f},{mem_used_mb:.2f},{mem_percent:.2f}\n"
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(log_line)
            
            # 等待下一个监控周期
            time.sleep(self.interval)

    def start(self):
        """启动监控"""
        self.running = True
        self.thread = threading.Thread(target=self._monitor, daemon=True)  # 守护线程，主程序结束后自动退出
        self.thread.start()
        print(f"资源监控已启动，日志文件：{self.log_path}")

    def stop(self):
        """停止监控"""
        self.running = False
        if self.thread:
            self.thread.join()
        print(f"资源监控已停止，日志已保存至：{self.log_path}")

def makeStubAsWithHosts(emu: Emulator, base: Base, asn: int, prefix: str, exchange: int, hosts_total: int):

    # Create AS and internal network
    network = "net0"

    stub_as = base.createAutonomousSystem(asn)
    stub_as.createNetwork(network,prefix)

    # Create a BGP router
    # Attach the router to both the internal and external networks
    router = stub_as.createRouter('r{}'.format(exchange))
    router.joinNetwork(network)
    router.joinNetwork('ix{}'.format(exchange),str(IPv4Network(node_prefix[exchange])[asn]))

    for counter in range(hosts_total):
       name = 'host_{}'.format(counter)
       host = stub_as.createHost(name)
       host.joinNetwork(network)

def makeTransitAs(base: Base, asn: int, prefix: str, exchanges: List[int],
    intra_ix_links: List[Tuple[int, int]],node_prefix=node_prefix) -> AutonomousSystem:
    """!
    @brief create a transit AS.

    @param base reference to the base layer.
    @param asn ASN of the newly created AS.
    @param exchanges list of IXP IDs to join.
    @param intra_ix_links list of tuple of IXP IDs, to create intra-IX links at.

    @returns transit AS object.
    """

    transit_as = base.createAutonomousSystem(asn)
    #transit_as.setSubnets(prefix)
    routers: Dict[int, Router] = {}

    # Create a BGP router for each internet exchange (for peering purpose)
    for ix in exchanges:
        routers[ix] = transit_as.createRouter('r{}'.format(ix))
        routers[ix].joinNetwork('ix{}'.format(ix),str(IPv4Network(node_prefix[ix])[asn]))
        #print(ix,str(IPv4Network(node_prefix[ix])[asn]))
        #raise ValueError

    # For each pair, create an internal network to connect the BGP routers
    # from two internet exchanges. There is no need to create a full-mesh
    # network among the BGP routers. As long as they can reach each other
    # over a single or multiple hops, it is OK.
    t=len(intra_ix_links)
    i=1
    subnets=list(IPv4Network(prefix).subnets(prefixlen_diff=8))
    for (a, b) in intra_ix_links:
        assert i<255, "net >= 255"
        name = 'net_{}_{}'.format(a, b)
        transit_as.createNetwork(name,str(subnets[i]))
        routers[a].joinNetwork(name)#,str(subnets[i][253])
        routers[b].joinNetwork(name)#,str(subnets[i][254])
        i+=1

    return transit_as

def find_maximal_cliques(edge_list):
    # 1. 创建一个无向图
    G = nx.Graph()

    # 2. 将列表 b 中的所有边添加到图中
    G.add_edges_from(edge_list)


    # 3. 查找图 G 中的所有极大团
    # nx.find_cliques(G) 返回一个生成器(generator)，每个元素是一个 set
    cliques_generator = nx.find_cliques(G)

    # 4. 将结果转换为列表，并对每个团内部进行排序（以便于查看）
    #    使用 sorted(list(clique)) 来匹配您期望的输出格式
    result = [sorted(list(clique)) for clique in cliques_generator]
    return result

def load_topology_data(filename: str) -> dict:
    """从文件加载拓扑数据（兼容 key: value 格式）"""
    with open(filename, 'r') as f:
        content = f.read().strip()
    
    # 处理格式：添加外层大括号，替换冒号为冒号+引号，处理列表
    # 1. 替换 key: 为 'key':
    content = re.sub(r'^(\w+):', r'"\1":', content, flags=re.MULTILINE)
    # 2. 每行末尾添加逗号（最后一行除外）
    lines = content.split('\n')
    lines = [line + ',' for line in lines[:-1]] + [lines[-1]] if lines else []
    content = '\n'.join(lines)
    # 3. 包裹成字典
    content = '{' + content + '}'
    
    # 安全解析为字典
    try:
        return eval(content)  # 此处使用eval是因为处理后的格式已符合Python字典规范
    except Exception as e:
        raise ValueError(f"解析拓扑数据失败: {e}")

def run(dumpfile=None, hosts_per_as=2): 
    ###############################################################################
    # 设置平台信息
    if dumpfile is None:
        script_name = os.path.basename(__file__)

        if len(sys.argv) == 1:
            platform = Platform.AMD64
        elif len(sys.argv) == 2:
            if sys.argv[1].lower() == 'amd':
                platform = Platform.AMD64
            elif sys.argv[1].lower() == 'arm':
                platform = Platform.ARM64
            else:
                print(f"用法:  {script_name} amd|arm")
                sys.exit(1)
        else:
            print(f"用法:  {script_name} amd|arm")
            sys.exit(1)

    # 加载拓扑数据
    try:
        TOPOLOGY_DATA = load_topology_data('real_topology_214.txt')
        TOPOLOGY_DATA = update_topology_from_file(TOPOLOGY_DATA,max_new_asns=50)
    except FileNotFoundError:
        print("错误: 未找到real_topology_1078.txt文件")
        sys.exit(1)
    except Exception as e:
        print(f"解析拓扑数据出错: {e}")
        sys.exit(1)

    
    emu   = Emulator()
    ebgp  = Ebgp()
    base  = Base()
    
    ###############################################################################
    # 创建互联网交换点(IXP)
    ix_objects = {}
    for ixp in TOPOLOGY_DATA["ixps"]:
        prefix = assignment[ixp]['ipv4']
        ix = assignment[ixp]['asn']
        address=str(IPv4Network(prefix)[ix])
        ix_obj = base.createInternetExchange(ix,prefix,rsAddress=address)
        ix_obj.getPeeringLan().setDisplayName(f'IX-{ix}')  # 设置显示名称
        ix_objects[ix] = ix_obj
        print(f"创建IXP: {ix} (显示名称: IX-{ix})")
    
    ###############################################################################
    # 收集Transit AS的连接信息
    transit_info = {}
    for asn in TOPOLOGY_DATA["transit_asns"]:
        asn = assignment[asn]['asn']
        connected_ixs = set()
        intra_links = []
        for (ix_a, ix_b, t_asn, _) in TOPOLOGY_DATA["ix_ix_transit_edges"]:
            ix_a = assignment[ix_a]['asn']
            ix_b = assignment[ix_b]['asn']
            t_asn = assignment[t_asn]['asn']
            if t_asn == asn:
                connected_ixs.add(ix_a)
                connected_ixs.add(ix_b)
                intra_links.append((ix_a, ix_b))
        transit_info[asn] = (sorted(connected_ixs), intra_links)
    # with open("transit_info.pkl", "rb") as f:
    #     transit_info = pickle.load(f)
    
    ###############################################################################
    # 创建Transit Autonomous Systems
    for asnuber in TOPOLOGY_DATA["transit_asns"]:
        asn = assignment[asnuber]['asn']
        prefix = assignment[asnuber]['ipv4']
        exchanges, intra_links = transit_info[asn]
        # temp=find_maximal_cliques(intra_links)
        # links=[]
        # for clique in temp:
        #     links.extend([(clique[i], clique[(i + 1) % len(clique)]) for i in range(len(clique))])
        links=[]
        clique=sorted(exchanges)
        links=generate_connected_pairs(clique, min(2*len(clique),253-len(clique)))
        makeTransitAs(base, asn, prefix, exchanges, list(set(links)))
        print(f"创建Transit AS{asn}: 连接IXP{exchanges}, 内部链路{links}")
    
    ###############################################################################
    # 创建Stub AS并添加主机

    stub_ix_map = {}
    for (provider, customer, ix, rel) in TOPOLOGY_DATA["as_as_ix_edges"]:
        if rel == '-1' and customer in TOPOLOGY_DATA["stub_asns"]:
            stub_ix_map[customer] = ix
    print(TOPOLOGY_DATA["stub_asns"])
    assignment_temp=assignment.copy()
    for stub_asn in TOPOLOGY_DATA["stub_asns"]:
        assignment_temp=get_assignment(stub_asn,assignment_temp)
        asn=assignment_temp[stub_asn]['asn']
        prefix=assignment_temp[stub_asn]['ipv4']
        ix = assignment_temp[stub_ix_map[stub_asn]]['asn']
        makeStubAsWithHosts(emu, base, asn, prefix, ix, hosts_per_as)
        print(f"创建Stub AS{asn}: 连接IXP{ix}, 主机数量{hosts_per_as}")
    
    # 配置私有对等关系
    for (a, b, ix, rel) in TOPOLOGY_DATA["as_as_ix_edges"]:
        a = assignment_temp[a]['asn']
        b = assignment_temp[b]['asn']
        ix = assignment_temp[ix]['asn']
        rel = int(rel)
        # 转换关系: -1→Provider, 0→Peer
        if rel == -1:
            relationship = PeerRelationship.Unfiltered
        elif rel == 0:
            relationship = PeerRelationship.Unfiltered###########
        else:
            raise ValueError(f"无效关系值: {rel} (仅支持-1和0)")
        
        ebgp.addPrivatePeerings(ix, [a], [b], relationship)
        print(f"IXP{ix}配置私有对等: AS{a}与AS{b} (关系: {rel})")

    #add_traffic(base, emu, TOPOLOGY_DATA["stub_asns"], assignment_temp, num=5)
    t=time.time()

    print("开始编译仿真网络...")
    ######################################################
    # #########################
    # 添加所有层到仿真器
    emu.addLayer(base)
    emu.addLayer(Routing())
    emu.addLayer(ebgp)
    emu.addLayer(Ibgp())
    emu.addLayer(Ospf())
    
    ###############################################################################
    # 输出结果
    if dumpfile is not None:
        # 保存到文件供其他仿真器使用
        emu.dump(dumpfile)
    else:
        emu.render()
        # 附加Internet Map容器并编译
        docker = Docker(platform=platform)
        emu.compile(docker, './output', override=True)
        print("仿真网络编译完成，输出目录: ./output")
    print(f"编译时间: {time.time()-t} 秒")

if __name__ == "__main__":
    # 初始化监控器（监控间隔1秒）
    monitor = ResourceMonitor(interval=1)
    # 启动监控
    monitor.start()
    try:
        run()
    finally:
        # 无论程序是否异常，确保监控停止
        monitor.stop()
