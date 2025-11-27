from seedemu.layers import Base, Routing, Ebgp, Ibgp, Ospf, PeerRelationship
from seedemu.compiler import Docker, Platform, Graphviz
from seedemu.core import Emulator
from seedemu.utilities import Makers
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
with open("assignment.pkl", "rb") as f:
    assignment = pickle.load(f)
node_prefix={}
for key,value in assignment.items():
    node_prefix[value['asn']]=value['ipv4']
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
        #print(name,str(subnets[i]),str(subnets[i][253]))
        #raise ValueError

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
        TOPOLOGY_DATA = load_topology_data('real_topology_1230.txt')
    except FileNotFoundError:
        print("错误: 未找到real_topology.txt文件")
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
        links.extend([(clique[i], clique[(i + 1)]) for i in range(len(clique)-1)])
        makeTransitAs(base, asn, prefix, exchanges, list(set(links)))
        print(f"创建Transit AS{asn}: 连接IXP{exchanges}, 内部链路{links}")
    
    ###############################################################################
    # 创建Stub AS并添加主机
    stub_ix_map = {}
    for (provider, customer, ix, rel) in TOPOLOGY_DATA["as_as_ix_edges"]:
        if rel == -1 and customer in TOPOLOGY_DATA["stub_asns"]:
            stub_ix_map[customer] = ix

    for stub_asn in TOPOLOGY_DATA["stub_asns"]:
        ix = stub_ix_map[stub_asn]
        Makers.makeStubAsWithHosts(emu, base, stub_asn, ix, hosts_per_as)
        print(f"创建Stub AS{stub_asn}: 连接IXP{ix}, 主机数量{hosts_per_as}")
    
    ###############################################################################
    # 配置RS多边对等关系
    # ix_as_map = {assignment[ix]['asn']: [] for ix in TOPOLOGY_DATA["ixps"]}
    # # 添加Transit AS
    # for asn in TOPOLOGY_DATA["transit_asns"]:
    #     asn = assignment[asn]['asn']
    #     for ix in transit_info[asn][0]:
    #         ix_as_map[ix].append(asn)
    # # 添加Stub AS
    # for stub_asn, ix in stub_ix_map.items():
    #     ix_as_map[ix].append(stub_asn)
    
    # # 应用RS对等配置
    # for ix, asns in ix_as_map.items():
    #     if asns:
    #         ebgp.addRsPeers(ix, asns)
    #         print(f"IXP{ix}配置RS多边对等: 参与AS{asns}")
    
    ###############################################################################
    # 配置私有对等关系
    for (a, b, ix, rel) in TOPOLOGY_DATA["as_as_ix_edges"]:
        a = assignment[a]['asn']
        b = assignment[b]['asn']
        ix = assignment[ix]['asn']
        rel = int(rel)
        # 转换关系: -1→Provider, 0→Peer
        if rel == -1:
            relationship = PeerRelationship.Provider
        elif rel == 0:
            relationship = PeerRelationship.Peer
        else:
            raise ValueError(f"无效关系值: {rel} (仅支持-1和0)")
        
        ebgp.addPrivatePeerings(ix, [a], [b], relationship)
        print(f"IXP{ix}配置私有对等: AS{a}与AS{b} (关系: {rel})")
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
        #emu.compile(docker, './output', override=True)
        emu.compile(Graphviz(), './output11')
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
