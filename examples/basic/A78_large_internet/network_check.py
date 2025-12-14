import docker
import re
import sys
import datetime

# ================= 配置区域 =================
# 注意：network_dict 现在将通过 get_docker_subnets 自动填充
# 如果需要手动补充特定路由，可以在 main 函数中合并数据
# ===========================================

def log_message(message, file_handle=None):
    """
    辅助函数：同时输出到控制台和日志文件
    """
    print(message)
    if file_handle:
        file_handle.write(message + "\n")
        file_handle.flush() # 确保实时写入

def get_docker_subnets(client, log_handle=None):
    """
    从 Docker 网络配置中自动提取网段信息。
    过滤条件：只提取掩码为 /24 的网段 (X.X.X.X/24)
    聚合逻辑：解析网络名称 output_net_{AS}_net_...，提取 AS 号并将相同 AS 的网段合并。
    返回格式: { '1271': ['5.247.10.0/24', '5.247.18.0/24'], ... }
    """
    dynamic_dict = {}
    networks = client.networks.list()
    
    # 正则用于提取AS号: 匹配 output_net_数字_net_
    as_pattern = re.compile(r"output_net_(\d+)_net_")

    log_message("[*] 正在扫描 Docker 网络并提取 /24 网段 (按 AS 聚合)...", log_handle)
    
    subnet_count = 0
    for net in networks:
        # 获取 IPAM (IP Address Management) 配置
        ipam = net.attrs.get('IPAM')
        if not ipam:
            continue
            
        # 获取 Config 配置
        configs = ipam.get('Config')
        if not configs:
            continue
        
        valid_subnets = []
        
        for config in configs:
            if not isinstance(config, dict):
                continue

            subnet = config.get('Subnet')
            # 核心过滤逻辑：只获取 /24 网段
            if subnet and subnet.endswith('/24'):
                valid_subnets.append(subnet)
        
        if valid_subnets:
            # === 修改点：解析网络名称并提取 AS 号 ===
            match = as_pattern.search(net.name)
            if match:
                # 提取第一个捕获组（数字部分）作为 Key，例如 "1271"
                key = match.group(1)
            else:
                # 如果不匹配特定格式，回退到使用原始网络名称
                key = net.name
            
            # === 修改点：聚合逻辑 ===
            # 如果 Key 已存在，则扩展列表；否则创建新列表
            if key in dynamic_dict:
                dynamic_dict[key].extend(valid_subnets)
            else:
                dynamic_dict[key] = valid_subnets
                
            subnet_count += len(valid_subnets)

    log_message(f"[*] 自动构建完成: 包含 {len(dynamic_dict)} 个 AS/组，共 {subnet_count} 条 /24 路由信息。", log_handle)
    for key in dynamic_dict:
        dynamic_dict[key]=sorted(dynamic_dict[key])
    return dynamic_dict

def get_target_containers(client, log_handle=None):
    """
    获取并过滤符合命名规范的容器。
    保留: as1868brd-r187-1.187.7.76 (即 ...-r... 形式)
    排除: as190brd-ix190-1.190.0.190 (即 ...-ix... 形式)
    """
    target_containers = []
    all_containers = client.containers.list()

    # 正则表达式解释：
    # ^as\d+brd      : 以 as开头，接数字，再接 brd
    # -r\d+-         : 关键特征，必须包含 -r 后接数字，再接横杠 (排除 -ix)
    # .* : 匹配剩余字符
    pattern = re.compile(r"^as\d+brd-r\d+-.*")

    log_message(f"[*] 正在扫描并过滤容器...", log_handle)
    for container in all_containers:
        name = container.name
        
        # 使用正则匹配名称
        if pattern.match(name):
            target_containers.append(container)
            # log_message(f"  [+] 匹配: {name}", log_handle) # 调试用
        # else:
            # log_message(f"  [-] 忽略: {name}", log_handle) # 调试用

    return target_containers

def check_routes(container, network_data, log_handle=None):
    """
    在指定容器内执行 birdc 命令检查路由
    :param network_data: 包含需检查网段的字典 {AS号/来源: [网段列表]}
    """
    try:
        container_name = container.name
        short_id = container.short_id
        
        reachable_count = 0
        total_checks = 0
        unreachable_details = []

        log_message(f"\n{'='*20} 正在检查: {container_name} ({short_id}) {'='*20}", log_handle)

        if not network_data:
            log_message("[!] 警告: 路由表(network_dict)为空，跳过检查。", log_handle)
            return

        # 遍历配置字典
        # source_name 现在主要是 AS 号 (例如 "1271")
        for source_name, prefix_list in network_data.items():
            for prefix in prefix_list:
                total_checks += 1
                
                # 构造 BIRD 命令
                cmd = f"birdc show route {prefix}"
                
                try:
                    # 在容器内执行命令
                    exit_code, output = container.exec_run(cmd)
                    result = output.decode('utf-8').strip()

                    # 为了显示美观，如果是纯数字 key，可以显示为 ASxxx
                    display_name = f"AS{source_name}" if source_name.isdigit() else source_name

                    # 判断逻辑
                    if result and prefix in result:
                        reachable_count += 1
                        log_message(f"[OK] {display_name} -> {prefix} 存在", log_handle)
                    else:
                        unreachable_details.append(f"{display_name} ({prefix})")
                        log_message(f"[X]  {display_name} -> {prefix} 不可达", log_handle)
                
                except Exception as e:
                    log_message(f"[!] 执行命令出错: {e}", log_handle)
                    unreachable_details.append(f"{source_name} ({prefix}) - EXEC ERROR")

        # 输出该容器的统计结果
        log_message("-" * 60, log_handle)
        log_message(f"容器 {container_name} 统计: 成功 {reachable_count}/{total_checks}", log_handle)
        
        if unreachable_details:
            log_message("[失败详情]:", log_handle)
            for item in unreachable_details:
                log_message(f" - {item}", log_handle)
        log_message("-" * 60, log_handle)

    except Exception as e:
        log_message(f"检查容器 {container.name} 时发生严重错误: {e}", log_handle)

if __name__ == "__main__":
    # 生成带时间戳的日志文件名
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"route_check_{timestamp}.log"

    print(f"[*] 日志将保存至: {log_filename}")

    try:
        # 打开日志文件准备写入
        with open(log_filename, "w", encoding="utf-8") as log_file:
            
            # 连接 Docker Daemon
            client = docker.from_env()

            # 1. 自动获取网段信息 (自动聚合相同 AS 的网段)
            network_dict = get_docker_subnets(client, log_handle=log_file)
            print(network_dict)

            # 2. 获取符合规则的容器列表
            containers = get_target_containers(client, log_handle=log_file)
            
            if not containers:
                log_message("未找到符合命名规则 (as...-r...-...) 的运行中容器。", log_file)
                sys.exit(0)

            log_message(f"[*] 共发现 {len(containers)} 个符合条件的容器，开始逐个检查...\n", log_file)

            # 3. 遍历容器进行检查，传入自动获取的 network_dict
            for container in containers:
                check_routes(container, network_dict, log_handle=log_file)
                
            log_message("\n[*] 所有任务完成。", log_file)

    except docker.errors.DockerException as e:
        print(f"Docker 连接错误: {e}")
        print("请确保 Docker 服务已启动，且当前用户有权限访问 Docker Socket。")
    except Exception as e:
        print(f"发生未知错误: {e}")