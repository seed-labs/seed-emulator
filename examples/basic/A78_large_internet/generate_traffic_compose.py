import yaml
import os
import shutil
import pickle
import re
import sys
# ==========================================
# 辅助类与函数 (YAML 格式化)
# ==========================================
class FoldedString(str): pass
class QuotedString(str): pass

with open("assignment.pkl", "rb") as f:
    assignment = pickle.load(f)
def get_assignment(asn,assignment=assignment):
    t=len(assignment)
    if asn not in assignment.keys():
        assignment[asn]={'asn':t+1,'ipv4':f'{(t+1) //256}.{(t+1) %256}.0.0/16'}
    return assignment
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

def quoted_presenter(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')

yaml.add_representer(QuotedString, quoted_presenter)

# ==========================================
# 核心逻辑
# ==========================================

# 1. 定义 start.sh 的模板
# 更新为 #!/bin/bash 以匹配你的需求
# 我们使用 {role_specific_command} 来区分发生器和接收器的启动逻辑
# 使用 {default_route} 来填入计算好的网关
START_SH_TEMPLATE = """#!/bin/bash
cat /tmp/etc-hosts >> /etc/hosts

if [ -f /interface_setup ]; then
    chmod +x /interface_setup
    /interface_setup
fi

# --- Role Specific Command ---
{role_specific_command}
# -----------------------------

ip rou del default 2> /dev/null
ip route add default via {default_route} dev net0

echo "ready! run 'docker exec -it $HOSTNAME /bin/zsh' to attach to this node" >&2
echo 0 > /proc/sys/net/ipv4/conf/all/rp_filter
echo 0 > /proc/sys/net/ipv4/conf/default/rp_filter
sysctl -w net.ipv4.ip_forward=1 > /dev/null 2>&1
sysctl -w net.ipv4.udp_rmem_min=4000 > /dev/null 2>&1
sysctl -w net.ipv4.udp_wmem_min=4000 > /dev/null 2>&1
sysctl -w net.ipv4.tcp_rmem="4096 131072 6291456" > /dev/null 2>&1
sysctl -w net.ipv4.tcp_wmem="4096 16384 4194304" > /dev/null 2>&1
tail -f /dev/null
"""

def get_subnet_str(ip):
    """
    根据 IP (x.y.z.k) 生成 /16 子网字符串 (x.y.0.0/16)
    用于 ifinfo.txt
    """
    parts = ip.split('.')
    return f"{parts[0]}.{parts[1]}.0.0/16"

def get_default_gateway(ip):
    """
    根据 IP 生成网关 (x.y.z.254)
    """
    return f"{ip.rsplit('.', 1)[0]}.254"

def prepare_config_files(nodes_config, base_dir="./traffic_config"):
    """
    在磁盘上创建文件夹并写入配置文件 (ifinfo, targets, hosts, start.sh)
    """
    # 1. 预处理：收集所有节点信息用于 etc-hosts，收集 receivers 用于 traffic-targets
    all_hosts_entries = []
    receivers_list = []

    for node in nodes_config:
        asn = str(node['asn'])
        node_name = node['node_name']
        ip = node['ip']
        
        # 构建 Hosts 条目
        host_entry = f"{ip} {asn}-{node_name} {node_name}"
        all_hosts_entries.append(host_entry)

        # 收集接收者
        if "receiver" in node_name:
            receivers_list.append(node_name)

    # 2. 实际文件生成
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)

    for node in nodes_config:
        asn = str(node['asn'])
        node_name = node['node_name']
        ip = node['ip']
        container_name = f"as{asn}h-{node_name}-{ip}"
        
        # 节点对应的配置目录
        node_dir = os.path.join(base_dir, container_name)
        if not os.path.exists(node_dir):
            os.makedirs(node_dir)
            # print(f"[+] Created dir: {node_dir}")

        # --- 生成 A: ifinfo.txt ---
        subnet = get_subnet_str(ip) # 假设你有这个函数
        ifinfo_content = f"net0:{subnet}:0:0:0"
        with open(os.path.join(node_dir, "ifinfo.txt"), "w") as f:
            f.write(ifinfo_content)

        # --- 生成 B: etc-hosts ---
        with open(os.path.join(node_dir, "etc-hosts"), "w") as f:
            f.write("\n".join(all_hosts_entries))

        # --- 生成 C: traffic-targets (修改点：根据 ID 筛选) ---
        if "generator" in node_name:
            # 假设命名格式严格为: ...-generator-{ID}
            # 例如: iperf-generator-6 -> 分割后取最后一个元素 '6'
            try:
                # 提取 generator 的 ID
                gen_id = node_name.split('generator-')[1] 
                
                # 筛选规则：Receiver 名字里必须包含 "receiver-{ID}-"
                # 这样可以防止 ID=1 匹配到 receiver-10-1
                target_prefix = f"receiver-{gen_id}-"
                
                my_targets = [r for r in receivers_list if target_prefix in r]
                
            except IndexError:
                # 如果名字格式不对，无法提取ID，则不写入或写入全部(视需求而定)
                print(f"Warning: Could not parse ID from {node_name}")
                my_targets = []

            with open(os.path.join(node_dir, "traffic-targets"), "w") as f:
                f.write("\n".join(my_targets))

        # --- 生成 D: start.sh ---
        default_route = get_default_gateway(ip) # 假设你有这个函数
        
        if "generator" in node_name:
            # 必须把脚本放在后台运行 (&)，并确保先设置好权限
            # 修正了之前的逻辑，确保路由配置完后再启动脚本（这里只是生成命令字符串，逻辑在START_SH_TEMPLATE里控制顺序）
            role_cmd = "chmod +x /root/traffic_generator_iperf3.sh\nsleep 2\n/root/traffic_generator_iperf3.sh &"
        else:
            role_cmd = "iperf3 -s -D --logfile /root/iperf3_receiver.log"

        start_sh_content = START_SH_TEMPLATE.format(
            default_route=default_route,
            role_specific_command=role_cmd
        )

        start_sh_path = os.path.join(node_dir, "start.sh")
        with open(start_sh_path, "w") as f:
            f.write(start_sh_content)
        os.chmod(start_sh_path, 0o755)

def generate_docker_compose_data(nodes_config):
    services = {}
    networks = {}
    BASE_DEPENDS_ON = "98a2693c996c2294358552f48373498d"

    for node in nodes_config:
        asn = str(node['asn'])
        ip = node['ip']
        node_name = node['node_name']
        
        # 统一使用一个镜像，或者根据需要区分
        # 如果你只有一个 Dockerfile 构建出的镜像，这里都用同一个名字即可
        if "generator" in node_name:
            node_class = "TrafficGenerator"
            image_name = 'iperf-generator2' 
        elif "receiver" in node_name:
            node_class = "TrafficReceiver"
            image_name = 'iperf-receiver2' # 如果接收器镜像不同，请保留；如果相同，请改为一致
        else:
            node_class = "Host"
            image_name = 'ubuntu'

        container_name = f"as{asn}h-{node_name}-{ip}"
        network_name = f"output_net_{asn}_net0"
        meta_class_str = f'["{node_class}"]'
        service_key = f"hnode_{asn}_{node_name}"

        # 构建 Volumes 列表
        # 注意：现在所有节点都挂载 start.sh
        volumes_list = [
            f'./traffic_config/{container_name}/ifinfo.txt:/ifinfo.txt',
            f'./traffic_config/{container_name}/etc-hosts:/tmp/etc-hosts',
            f'./traffic_config/{container_name}/start.sh:/start.sh' # 挂载生成的启动脚本
        ]
        
        # 只有 Generator 需要挂载 traffic-targets
        if "generator" in node_name:
            volumes_list.append(f'./traffic_config/{container_name}/traffic-targets:/root/traffic-targets')

        service_def = {
            "image": image_name,
            "container_name": container_name,
            "cap_add": ["ALL"],
            "privileged": True,
            "networks": {
                network_name: {
                    "ipv4_address": ip
                }
            },
            "volumes": volumes_list,
            # 直接执行挂载进去的 start.sh，因为挂载到根目录，所以直接用绝对路径 /start.sh
            # 无论 Dockerfile 中是否注释掉 CMD，这里都会强制覆盖执行此命令
            "command": ["/start.sh"],
            "labels": {
                "org.seedsecuritylabs.seedemu.meta.asn": QuotedString(asn),
                "org.seedsecuritylabs.seedemu.meta.nodename": QuotedString(node_name),
                "org.seedsecuritylabs.seedemu.meta.role": QuotedString("Host"),
                "org.seedsecuritylabs.seedemu.meta.class": QuotedString(meta_class_str),
                "org.seedsecuritylabs.seedemu.meta.net.0.name": QuotedString("net0"),
                "org.seedsecuritylabs.seedemu.meta.net.0.address": QuotedString(f"{ip}/16")
            },
            "environment": [
                f"CONTAINER_NAME={container_name}"
            ]
        }
        
        services[service_key] = service_def
        if network_name not in networks:
            networks[network_name] = {"external": True}

    return {"services": services, "networks": networks}

# ==========================================
# 主程序入口
# ==========================================
if __name__ == "__main__":
    # 1. 配置输入
    TOPOLOGY_DATA = load_topology_data('real_topology_214.txt')
    TOPOLOGY_DATA = update_topology_from_file(TOPOLOGY_DATA,max_new_asns=50)
    assignment_temp=assignment.copy()
    for stub_asn in TOPOLOGY_DATA["stub_asns"]:
        assignment_temp=get_assignment(stub_asn,assignment_temp)
        asn=assignment_temp[stub_asn]['asn']
        prefix=assignment_temp[stub_asn]['ipv4']
    user_inputs=[]
    stubAS=TOPOLOGY_DATA["stub_asns"]
    num=len(stubAS)//3
    for i in range(num):
        asnum1=assignment_temp[stubAS[3*i]]['asn']
        asnum2=assignment_temp[stubAS[3*i+1]]['asn']
        asnum3=assignment_temp[stubAS[3*i+2]]['asn']
        ip1=assignment_temp[stubAS[3*i]]['ipv4'].split('/')[0].rsplit('.',1)[0]+'.150'
        ip2=assignment_temp[stubAS[3*i+1]]['ipv4'].split('/')[0].rsplit('.',1)[0]+'.150'
        ip3=assignment_temp[stubAS[3*i+2]]['ipv4'].split('/')[0].rsplit('.',1)[0]+'.150'
        node_name1=f"iperf-generator-{i}"
        node_name2=f"iperf-receiver-{i}-1"
        node_name3=f"iperf-receiver-{i}-2"
        user_inputs.append({"asn":asnum1,"ip":ip1,"node_name":node_name1})
        user_inputs.append({"asn":asnum2,"ip":ip2,"node_name":node_name2})
        user_inputs.append({"asn":asnum3,"ip":ip3,"node_name":node_name3})

    print("--- 步骤 1: 生成本地配置文件 (traffic_config/) ---")
    prepare_config_files(user_inputs)
    print("配置文件生成完毕。已为每个节点创建 start.sh。\n")

    print("--- 步骤 2: 生成 docker-compose.yml ---")
    compose_data = generate_docker_compose_data(user_inputs)
    
    # 写入文件
    yaml_output = yaml.dump(compose_data, sort_keys=False, default_flow_style=False, allow_unicode=True)
    
    with open('docker-compose-generated.yml', 'w') as f:
        f.write(yaml_output)
    
    print("YAML 文件已生成: docker-compose-generated.yml")
    print("使用方法: docker-compose -f docker-compose-generated.yml up -d")