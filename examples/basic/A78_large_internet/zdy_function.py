import networkx as nx
import matplotlib.pyplot as plt
import pickle  # 导入 pickle 模块
from collections import defaultdict
import ast  # 用于安全地解析 (AS, loc) 元组字符串
import io   # 仅用于示例
import random
import math
import time
import re
from collections import Counter
def get_summaryInfo(new_tuples):
    # 结构: {AS_a: {AS_b: [(IX, relationship), ...]}}
    adj_relationships = defaultdict(lambda: defaultdict(list))
    for u, v, ix, rel in new_tuples:
        adj_relationships[u][v].append((ix, rel))
        if rel == '0':
            inv_rel = '0'   # 对等关系，反向也是对等
        elif rel == '-1':
            inv_rel = '1'   # u给v提供服务(-1)，则v接受服务(1)
        elif rel == '1':
            inv_rel = '-1'  # 如果原数据有1，则反向为-1
        else:
            inv_rel = rel   # 未知情况保持原样   
        adj_relationships[v][u].append((ix, inv_rel))
    # 将 defaultdict 转换为普通 dict 以便查看或后续使用
    final_result = {k: dict(v) for k, v in adj_relationships.items()}
    ix_statistics = defaultdict(list)
    for u, v, ix, rel in new_tuples:
        # 将元组 (AS a, AS b, relationship) 添加到对应的 IX 键下
        ix_statistics[ix].append((u, v, rel))
    # 转换为普通字典 (可选)
    final_ix_stats = dict(ix_statistics)
    ix_counts = {k: len(v) for k, v in ix_statistics.items()}
    # 统计 AS 的邻居数 (Node Degree)
    # Key: AS号, Value: 该字典的长度 (即该AS有多少个邻居)
    as_neighbor_counts = {k: len(v) for k, v in final_result.items()}

    # ---------------------------------------------------------
    # (额外) 深度统计：如果您想知道每个 AS 总共有多少条物理连接 (即sum all lists)
    # ---------------------------------------------------------
    as_total_links = {}
    for as_node, neighbors in final_result.items():
        # 计算该 AS 下所有邻居里 list 长度的总和
        total_count = sum(len(links) for links in neighbors.values())
        as_total_links[as_node] = total_count

    ix_top_as_dict = {}
    for ix, links in ix_statistics.items():
        # 收集该 IX 下所有的 AS (展平)
        participants = []
        for u, v, _ in links:
            participants.extend([u, v])
        if not participants:
            continue
        # Counter.most_common(1) 返回一个列表：[(元素, 次数)]
        # 我们取 [0][0] 直接拿到 元素(AS号)
        # 如果有并列，它会自动只取其中一个，无需人工干预
        top_as = Counter(participants).most_common(1)[0][0]
        ix_top_as_dict[ix] = top_as
    return final_result, final_ix_stats, ix_counts, as_neighbor_counts, as_total_links, ix_top_as_dict
def add_rel(new_G,new_asSet,final_result,new_tuples,ix_as_members,ix_counts):
    add_AS=new_asSet-set(final_result.keys())
    AS_IX_dict=defaultdict(set)
    for node,data in new_G.nodes(data=True):
        if data['type']=='router':
            asn=data['as_num']
            if asn in add_AS:
                for nbr in new_G.neighbors(node):
                    if new_G.nodes[nbr]['type']=='ix':
                        AS_IX_dict[asn].add(nbr)
                        break
    paths=[]
    for asn, ix_list in AS_IX_dict.items():
        # key=... : 使用 ix_counts.get(ix, 0) 获取大小，如果没有则算作 0
        largest_ix = max(ix_list, key=lambda ix: ix_counts.get(ix, 0))
        # 获取这个 IX 对应的大小 (仅用于展示)
        max_size = ix_counts.get(largest_ix, 0)
        # 存入结果: {AS: (最大的IX名称, 大小)}
        paths.append((asn, ix_as_members[largest_ix], largest_ix, '0'))
    print(paths)
    new_tuples.extend(paths)
    print(f'为 {len(add_AS)} 个缺失 AS 添加了连接信息。')
    return new_tuples

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
    
def add_peer_info_to_ix_nodes(graph, peer_info_dict):
    """
    将从 pickle 文件加载的字典中的 peering 信息
    添加为图中相应 'ix' 节点的属性。

    参数:
        graph (nx.Graph): 要修改的二分图 (例如 B)。
        peer_info_dict (dict): 从 pickle 加载的字典。
                              格式: {'loc': [('N1', 'N2', 'rel'), ...]}
    """
    print("\n--- 正在将 Peering 信息添加到 IX 节点属性 ---")
    
    nodes_updated = 0
    nodes_not_found = 0
    
    # 遍历字典
    # loc 键 (例如 'Newark-DE-US')
    # info_list 值 (例如 [('N1', 'N2', '-1'), ...])
    for loc, info_list in peer_info_dict.items():
        
        # 'loc' 应该是图中 IX 节点的 ID
        if graph.has_node(loc):
            
            # 检查该节点是否确实是 'ix' 类型
            if graph.nodes[loc].get('type') == 'ix':
                
                # *** 核心操作 ***
                # 将信息列表存储为节点的新属性，命名为 'peer_info'
                graph.nodes[loc]['peer_info'] = info_list
                nodes_updated += 1
                
            else:
                # 这种情况不应该发生，但作为安全检查
                print(f"警告：节点 {loc} 存在，但类型不是 'ix' (类型为 {graph.nodes[loc].get('type')})。")
                
        else:
            # 如果 .pkl 文件和图的来源文件不一致，可能会发生这种情况
            print(f"警告：在图中找不到IX节点 {loc}。该地点的Peering信息未添加。")
            nodes_not_found += 1

    print(f"--- 操作完成 ---")
    print(f"成功更新 {nodes_updated} 个IX节点的属性。")
    if nodes_not_found > 0:
        print(f"{nodes_not_found} 个地点在图中未找到对应的IX节点。")
        
    return graph # 返回修改后的图

def calculate_as_ix_connections(graph):
    """
    统计图中每个 AS 连接了多少个 *唯一* 的 IX 节点。

    参数:
        graph (nx.Graph): 包含 'router' 和 'ix' 节点的图。

    返回:
        dict: 一个字典 {as_num: ix_count}
    """
    print("\n--- 正在统计每个AS连接的IX数量 ---")
    
    # 结构: {as_num: set_of_ix_names}
    # 使用 set 确保唯一性 (例如，AS '100' 的两个 router 都连到 'Newark'，只算1次)
    as_to_ixs = defaultdict(set)
    
    # 遍历所有节点
    for node_id, data in graph.nodes(data=True):
        
        # 1. 只关心 'router' 节点
        if data.get('type') == 'router':
            as_num = data.get('as_num')
            if not as_num:
                print(f"警告：Router {node_id} 缺少 'as_num' 属性，已跳过。")
                continue
            
            # 2. 遍历这个 router 的所有邻居
            for neighbor_id in graph.neighbors(node_id):
                
                # 3. 检查邻居是否为 'ix'
                try:
                    neighbor_data = graph.nodes[neighbor_id]
                    if neighbor_data.get('type') == 'ix':
                        
                        # 4. 如果是，将 IX 的名字添加到该 AS 的集合中
                        as_to_ixs[as_num].add(neighbor_id)
                        
                except KeyError:
                    # 如果邻居不在 .nodes() 中 (这不应该发生)
                    print(f"警告：节点 {node_id} 的邻居 {neighbor_id} 数据异常。")
    
    print("--- 统计完成 ---")
    
    # (可选) 返回按IX数量排序的列表
    # sorted_counts = sorted(as_ix_counts.items(), key=lambda item: item[1], reverse=True)
    return as_to_ixs
def create_subgraph_from_sets(original_graph, ix_set, router_set):
    """
    将 ix_set 和 router_set 合并，并从原始图中提取子图。
    """
    
    # 步骤 1: 将两个 set 合并为 all_nodes
    # 使用 set 的 union ( | ) 操作符
    all_nodes = ix_set | router_set
    
    print(f"\n--- 正在创建子图 ---")
    print(f"总共保留 {len(all_nodes)} 个节点。")
    
    # 步骤 2: 使用 G.subgraph() 构造新图
    # .subgraph() 返回的是一个“视图”(view)，它依赖于原图。
    # 我们使用 .copy() 来创建一个完全独立的新图，
    # 这样对新图的修改不会影响原图。
    new_graph = original_graph.subgraph(all_nodes).copy()
    
    print(f"新图创建成功，包含 {new_graph.number_of_nodes()} 个节点 和 {new_graph.number_of_edges()} 条边。")
    
    return new_graph
def categorize_and_expand_nodes(nodes_list, graph):
    """
    根据节点列表和图，构造并扩展 ix 节点集和 router 节点集。

    执行顺序:
    1. 初始分类
    2. 基于 ASN 扩展 router_set
    3. 基于邻居扩展 ix_set
    """
    ix_nodes_set = set()
    router_nodes_set = set()
    as_numbers = set()

    # --- 步骤 1: 初始分类 ---
    # 遍历您提供的 nodes 列表，进行初步分类
    for node_id in nodes_list:
        if node_id not in graph:
            print(f"警告: 节点 {node_id} 在列表中，但不在图中。")
            continue
        
        # 使用 .get() 避免 'type' 属性不存在时出错
        node_type = graph.nodes[node_id].get('type')

        if node_type == 'ix':
            ix_nodes_set.add(node_id)
        elif node_type == 'router':
            router_nodes_set.add(node_id)

    print(f"步骤 1: 初始 ix_set: {len(ix_nodes_set)}")
    print(f"步骤 1: 初始 router_set: {len(router_nodes_set)}")

    # --- 步骤 2: Router 扩展 (基于 ASN) ---
    
    # 2a. 从初始的 router_set 收集 ASN
    # 注意：这里我们遍历 router_nodes_set (此时只包含列表中的router)
    for router_id in router_nodes_set:
        asn = graph.nodes[router_id].get('as_num')
        if asn is not None:
            as_numbers.add(asn)
            
    print(f"步骤 2a: 收集到的 ASNs: {len(as_numbers)}")

    # 2b. 遍历图中的所有节点，用收集到的 ASN 扩展 router_set
    # 注意：这里我们遍历 graph.nodes() (图中的所有节点)
    for node_id, data in graph.nodes(data=True):
        node_asn = data.get('as_num')
        # 如果一个节点的ASN在我们的目标集合中...
        if node_asn in as_numbers:
            # ...就把它加入 router_set (即使它不在原始 nodes 列表中)
            router_nodes_set.add(node_id)

    print(f"步骤 2b: 扩展后的 router_set: {len(router_nodes_set)}")

    # --- 步骤 3: IX 扩展 (基于邻居) ---
    # 遍历*最终扩展后*的 router_nodes_set
    # 我们需要一个 router_set 的副本或列表来进行迭代，
    # 因为在技术上我们不应该在迭代时修改 set (尽管这里修改的是 ix_set)
    # 为了安全起见，使用 list(router_nodes_set)
    
    for router_id in list(router_nodes_set):
        # 遍历该 router 的所有邻居
        for neighbor_id in graph.neighbors(router_id):
            if neighbor_id not in graph:
                continue
            
            # 关键：检查邻居的类型是否为 'ix'
            # (因为您提到邻居也可能是 router)
            neighbor_type = graph.nodes[neighbor_id].get('type')
            if neighbor_type == 'ix':
                ix_nodes_set.add(neighbor_id)

    print(f"步骤 3: 扩展后的 ix_set: {len(ix_nodes_set)}")

    return router_nodes_set, ix_nodes_set, as_numbers

def forward_single(seeds, graph):
    #s=time.time()
    result = []
    result.extend(seeds)
    PRS_routers = list(seeds)
    
    # 对应 RRS 算法中的 result_list (BFS 队列)
    # 我们需要存储 (node, prev_node) 来为规则2提供记忆
    queue = [(seed, None) for seed in seeds] 
    
    # 对应 RRS 算法中的 checked (防止重复入队)
    checked = set(seeds)
    
    head = 0 # 使用列表模拟队列
    
    # 2. 对应 RRS 算法中的 while 循环
    while len(queue) > 0:
        # 对应 RRS 算法中的 current_node = result_list.pop(0)
        (current_node, prev_node_for_rules) = queue.pop(0)
        head += 1
        
        # 3. 对应 RRS 算法中的 for nbr in g.predecessors(current_node)
        # 我们用 *正向* 激活逻辑 (get_custom_next_hops) 替代
        activated_hops = get_custom_next_hops(graph, current_node, prev_node_for_rules, forward=True)
        
        for next_hop in activated_hops:
            # 4. 对应 RRS 算法中的 if checked[nbr] == 0:
            if next_hop not in checked :
                
                # 5. 对应 RRS 算法中的 result_list.append(nbr)
                if graph.nodes[next_hop]['type']!='ix':
                    checked.add(next_hop)
                queue.append((next_hop, current_node)) # (next_hop, 它的激活者)
                
                # 6. 对应 RRS 算法中的 RRS.append(nbr)
                PRS_routers.append(next_hop)
    return PRS_routers
def select_nodes(seeds, graph, try_num=10000):
    RRS = [forward_single(seeds, graph) for _ in range(try_num)]
    flat_map = [item for subset in RRS for item in subset if graph.nodes[item].get('type') == 'router']
    if(len(flat_map))==0:
        print('RRS is NULL')
        return 0
    temp = Counter(flat_map).most_common()
    return temp

def optimized_nodeselect(k, a, b, cover_counts, remaining_rrs):
    """无需复制原始映射，仅在内部维护临时状态"""
    s = time.time()
    SEED = []
    total_covered = 0
    
    # 仅复制需要修改的状态（覆盖计数和剩余RR集）
    current_cover = cover_counts.copy()  # 复制需要修改的计数
    current_remaining = remaining_rrs.copy()  # 复制需要修改的集合
    
    for _ in range(k):
        if not current_remaining or not current_cover:
            break
        
        # 选择覆盖最多的节点
        seed = max(current_cover, key=lambda x: current_cover[x])
        SEED.append(seed)
        
        # 找到覆盖的RR集
        covered_rrs = [rr_idx for rr_idx in a[seed] if rr_idx in current_remaining]
        total_covered += len(covered_rrs)
        
        # 更新剩余RR集
        for rr_idx in covered_rrs:
            current_remaining.discard(rr_idx)
        
        # 更新其他节点的覆盖计数
        for rr_idx in covered_rrs:
            for node in b[rr_idx]:
                if node != seed and node in current_cover:
                    current_cover[node] -= 1
                    if current_cover[node] == 0:
                        del current_cover[node]
        
        # 移除已选节点
        del current_cover[seed]
    
    #print(f"节点选择耗时: {time.time() - s:.2f}秒")
    return SEED, total_covered

def combination(n, k):
    if k < 0 or k > n:
        return 0
    # 利用对称性，C(n, k) == C(n, n-k)
    if k > n - k:
        k = n - k
    result = 1
    for i in range(1, k + 1):
        result = result * (n - i + 1) // i
    return result
def lnc(n,k):
    return math.log(combination(n, k))

def IMM_RRS(G,k,eps,ell,node_list):
    n=len(G.nodes)
    s = time.time()
    # 参数计算（保持不变）
    ell=ell*(1+math.log(2)/math.log(n))
    eps1=math.sqrt(2) * eps
    alpha = math.sqrt(ell * math.log(n) + math.log(2))
    beta = math.sqrt((1.0 - 1.0 / math.exp(1)) * (lnc(n,k) + alpha * alpha))
    lamba1 = (2*n*(1+1/3*eps1) * (lnc(n,k)+ell*math.log(n)+math.log(math.log(n)/math.log(2))))/(eps1*eps1)
    lamba2 = 2 * n * pow(((1.0 - 1.0 / math.exp(1)) * alpha + beta),2) / (eps*eps)
    LB=1
    # 初始化映射（b直接存储RR集，a和cover_counts实时更新）
    a = defaultdict(list)  # a[node] = [rrset_idx1, ...]
    b = []  # b[rr_idx] = [node1, ...]（替代原R）
    cover_counts = defaultdict(int)  # 节点覆盖计数
    
    len_b=0
    # 校准阶段
    for i in range(1, int(math.log(n-1) / math.log(2)) + 1):
        x = n / pow(2, i)
        ti = int(lamba1 / x)
        # 生成RR集并实时更新映射
        
        while len_b < ti:
            rrset = get_probabilistic_reachable_set(G, node_list, forward=False)
            b.append(rrset)
            for node in rrset:
                a[node].append(len_b)
                cover_counts[node] += 1
            len_b=len(b)
        
        # 无需复制，直接传递原始映射（函数内部不会修改它们）
        remaining_rrs = set(range(len(b)))
        SEED, js = optimized_nodeselect(k, a, b, cover_counts, remaining_rrs)
        
        if n * js / len(b) >= (1 + eps1) * x:
            LB = n * js / ((1 + eps1) * len(b))
            break
    
    # 最终采样阶段
    theta = int(lamba2 / LB)
    print(f"len(RR): {theta}")
    
    # 继续生成RR集至目标数量
    
    while len_b < theta:
        rrset = get_probabilistic_reachable_set(G, node_list, forward=False)
        b.append(rrset)
        for node in rrset:
            a[node].append(len_b)
            cover_counts[node] += 1
        len_b=len(b)
    
    # 最终种子选择（同样无需复制）
    remaining_rrs = set(range(len(b)))
    seed, js = optimized_nodeselect(k, a, b, cover_counts, remaining_rrs)
    print(f"覆盖节点数: {n * js / len(b)}")
    print(f"IMM_RRS COST TIME: {time.time() - s:.2f}s")
    return seed

def get_custom_next_hops(graph, current_node, prev_node,forward=True):
    """
    (核心规则) 根据您的伪代码，获取所有可能的、已激活的下一跳。
    这是实现您规则 1 和 2 的地方。
    """
    
    # 验证 current_node 是否存在
    if not graph.has_node(current_node):
        return []

    current_data = graph.nodes[current_node]
    current_type = current_data.get('type')
    valid_hops = []

    # 规则 1：如果当前在 'router'
    if current_type == 'router':
        for nbr in graph.neighbors(current_node):
            if nbr == prev_node:
                continue
            
            nbr_data = graph.nodes[nbr]
            nbr_type = nbr_data.get('type')
            edge_data = graph.edges[current_node, nbr]
            edge_weight = edge_data.get('weight', 0)
            
            # 规则 1.A: Router -> Router (internal_as)
            if nbr_type == 'router':
                if edge_data.get('relation') == 'internal_as':
                    if random.random() < edge_weight:
                        valid_hops.append(nbr)
            
            # 规则 1.B: Router -> IX
            elif nbr_type == 'ix':
                if random.random() < edge_weight:
                    valid_hops.append(nbr)

    # 规则 2：如果当前在 'ix'
    elif current_type == 'ix':
        # 必须是从一个 router (prev_node) 来的
        if prev_node is None or graph.nodes[prev_node].get('type') != 'router':
            return [] # 无法应用规则
        
        source_router = prev_node
        peer_info_list = current_data.get('peer_info', [])
        
        # 优化：为 source_router 创建一个快速查找的可达对等方集合
        reachable_peers = set()
        for (n_a, n_b, rel) in peer_info_list:
            if forward == True: #正向采样
                if n_a == source_router:
                    reachable_peers.add(n_b)
                elif n_b == source_router and rel == '0':  # 仅对等关系
                    reachable_peers.add(n_a)
            else: #反向采样
                if n_b == source_router:
                    reachable_peers.add(n_a)
                elif n_a == source_router and rel == '0':  # 仅对等关系
                    reachable_peers.add(n_b)

        # 遍历邻居 (寻找 target_router)
        for target_router in graph.neighbors(current_node):
            if target_router == source_router:
                continue
            
            # 确保目标是 router
            if graph.nodes[target_router].get('type') != 'router':
                continue
            
            # (根据您的澄清，我们不再需要检查AS，因为它们总是不同的)
            
            # 规则 2.A: 检查 peer_info 可达性
            if target_router in reachable_peers:
                
                # 规则 2.B: 检查 (IX, target_router) 边的 weight 激活
                edge_weight = graph.edges[current_node, target_router].get('weight', 0)
                
                if random.random() < edge_weight:
                    valid_hops.append(target_router)

    return valid_hops

def get_probabilistic_reachable_set(graph, router_list, forward=True):
    """
    (您的RRS算法)
    实现您的 RRS 结构，但使用 get_custom_next_hops 作为激活逻辑。
    这模拟了一个从 seed 出发的概率扩散过程。
    """
    
    # 1. 选择一个 'router' 类型的 seed
    seed = random.choice(router_list)
    
    # 对应 RRS 算法中的 RRS 集合 (我们只存储 router)
    PRS_routers = [seed]
    
    # 对应 RRS 算法中的 result_list (BFS 队列)
    # 我们需要存储 (node, prev_node) 来为规则2提供记忆
    queue = [(seed, None)] 
    
    # 对应 RRS 算法中的 checked (防止重复入队)
    checked = {seed}
    
    head = 0 # 使用列表模拟队列
    
    # 2. 对应 RRS 算法中的 while 循环
    while len(queue) > 0:
        # 对应 RRS 算法中的 current_node = result_list.pop(0)
        (current_node, prev_node_for_rules) = queue.pop(0)
        head += 1
        
        # 3. 对应 RRS 算法中的 for nbr in g.predecessors(current_node)
        # 我们用 *正向* 激活逻辑 (get_custom_next_hops) 替代
        activated_hops = get_custom_next_hops(graph, current_node, prev_node_for_rules, forward=forward)
        
        for next_hop in activated_hops:
            # 4. 对应 RRS 算法中的 if checked[nbr] == 0:
            if next_hop not in checked:
                
                # 5. 对应 RRS 算法中的 result_list.append(nbr)
                if graph.nodes[next_hop]['type']!='ix':
                    checked.add(next_hop)
                queue.append((next_hop, current_node)) # (next_hop, 它的激活者)
                
                # 6. 对应 RRS 算法中的 RRS.append(nbr)
                # (我们只在 RRS 集合中存储 router)
                if graph.nodes[next_hop].get('type') == 'router':
                    PRS_routers.append(next_hop)
                    
    return list(PRS_routers)

def build_bipartite_from_file(filepath):
    """
    (已修正)
    基于 as_geo_results_with_rel.txt 文件构建二分图。
    该文件应同时包含节点映射表和关系表。
    """
    print(f"正在从 {filepath} 读取数据构建二分图...")
    
    # 创建空的无向图
    B = nx.Graph()
    
    # 状态标记
    in_mapping_section = False
    in_relations_section = False

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # --- 状态机：切换解析模式 ---
                if line.startswith("=== 节点映射表 ==="):
                    in_mapping_section = True
                    in_relations_section = False
                    print("...正在解析节点映射表...")
                    continue
                
                if line.startswith("=== 关系表 (N1, N2, IXP, Relationship) ==="):
                    in_mapping_section = False
                    in_relations_section = True
                    print("...正在解析关系表...")
                    continue
                    
                if not line or (not in_mapping_section and not in_relations_section):
                    continue

                # --- 模式一：解析节点 (来自节点映射表) ---
                if in_mapping_section:
                    try:
                        # 格式: N1: (2, Newark-DE-US)
                        parts = line.split(":", 1)
                        if len(parts) != 2:
                            raise ValueError("行中缺少 ':' 分隔符")
                            
                        node_id = parts[0].strip()    # "N1"
                        info_str = parts[1].strip()   # " (2, Newark-DE-US)"
                        
                        # --- 关键修改：手动解析 (AS, loc) ---
                        
                        # 1. 确保它以 ( 和 ) 包裹
                        if not info_str.startswith("(") or not info_str.endswith(")"):
                            raise ValueError("映射值不是以 '(' 和 ')' 包裹")
                            
                        # 2. 去除括号 " (2, Newark-DE-US)" -> "2, Newark-DE-US"
                        #    我们先 strip() 再切片 [1:-1]
                        info_inner_str = info_str.strip()[1:-1] 
                        
                        # 3. 按第一个逗号分割
                        info_parts = info_inner_str.split(",", 1)
                        if len(info_parts) != 2:
                            raise ValueError("映射元组中缺少 ','")
                            
                        as_num = info_parts[0].strip() # "2"
                        loc = info_parts[1].strip()    # "Newark-DE-US"
                        
                        # --- 修改结束 ---
                        
                        # 添加节点 (与原函数逻辑相同)
                        B.add_node(node_id, type='router', as_num=as_num)
                        B.add_node(loc, type='ix')
                        
                    except (ValueError, SyntaxError, IndexError) as e:
                        print(f"警告：跳过格式错误的映射行: {line} -> 错误: {e}")
                        continue
                        
                # --- 模式二：解析边 (来自关系表) ---
                if in_relations_section:
                    try:
                        # 格式: N1, N2, Newark-DE-US, -1
                        parts = line.split(",")
                        
                        if len(parts) != 4:
                            raise ValueError(f"行应有4个部分，但得到了 {len(parts)} 个")
                            
                        n1 = parts[0].strip()
                        n2 = parts[1].strip()
                        ixp = parts[2].strip()
                        relationship = parts[3].strip()
                        
                        # 检查节点是否已在图中
                        # (如果映射表是完整的，它们应该都在)
                        if not B.has_node(n1):
                            print(f"警告: 节点 {n1} (在关系表中) 未在映射表中定义。")
                        if not B.has_node(n2):
                            print(f"警告: 节点 {n2} (在关系表中) 未在映射表中定义。")
                        if not B.has_node(ixp):
                            # IXP 节点应该由映射表创建
                            print(f"警告: IXP {ixp} (在关系表中) 未在映射表中定义。将自动添加。")
                            B.add_node(ixp, type='ix') # 自动添加
                        
                        B.add_edge(n1, ixp)
                        B.add_edge(n2, ixp)
                        
                    except (ValueError, IndexError) as e:
                        print(f"警告：跳过格式错误的关系行: {line} -> 错误: {e}")
                        continue

    except FileNotFoundError:
        print(f"错误：找不到文件 {filepath}")
        return None
    except Exception as e:
        print(f"打开或读取文件时发生未知错误: {e}")
        return None
    
    print("二分图构建完成！")
    return B

def analyze_bipartite_graph(B):
    """分析二分图的基本属性"""
    if not B:
        return
    
    print("\n--- 二分图基本信息 ---")
    print(f"总节点数: {B.number_of_nodes()}")
    print(f"总边数: {B.number_of_edges()}")
    
    # 验证是否为二分图
    is_bipartite = nx.is_bipartite(B)
    print(f"是否为二分图: {is_bipartite}")
    
    # 分离AS节点和IX节点
    as_nodes = {n for n, d in B.nodes(data=True) if d['type'] == 'router'}
    ix_nodes = {n for n, d in B.nodes(data=True) if d['type'] == 'ix'}

    print(f"AS节点数: {len(as_nodes)}")
    print(f"IX节点数: {len(ix_nodes)}")

    # 输出连接最多AS的Top10 IX
    print("\n--- Top 10 交换中心（按连接的AS数量）---")
    if ix_nodes:
        ix_degrees = sorted(
            [(ix, B.degree(ix)) for ix in ix_nodes],
            key=lambda x: x[1],
            reverse=True
        )
        for i, (ix, degree) in enumerate(ix_degrees[:10]):
            print(f"{i+1}. {ix}: 连接 {degree} 个AS")
    else:
        print("未找到IX节点")

def generate_connected_pairs(nodes, extra_edges_count=0):
    """
    生成随机连接对，确保图是连通的。
    :param nodes: 节点列表
    :param extra_edges_count: 在保证连通后，额外增加多少条随机边
    """
    if len(nodes) < 2:
        return []

    # 复制一份节点列表以免修改原数据
    unconnected = nodes[:]
    random.shuffle(unconnected) # 打乱顺序以增加随机性
    
    # 1. 初始化：选一个起点放入“已连接集合”
    connected = [unconnected.pop()]
    
    pairs = set() # 使用集合避免重复边

    # 2. 构建骨干网络 (随机生成树)
    # 只要还有未连接的节点，就从中取出一个，连到已连接集合中的任意一个节点上
    while unconnected:
        # 取出一个未连接的节点
        new_node = unconnected.pop()
        
        # 从已连接的节点中随机选一个作为邻居
        partner = random.choice(connected)
        
        # 生成边 (排序以确保 (A, B) 和 (B, A) 视为同一个)
        pair = tuple(sorted((new_node, partner)))
        pairs.add(pair)
        
        # 将新节点加入已连接集合
        connected.append(new_node)
        
    # 此时，所有节点已连通，且边数最少 (N-1 条边)
    
    # 3. (可选) 添加额外的随机边，增加网络复杂度
    # 如果您只需要最基本的连通，可以让 extra_edges_count = 0
    current_edge_count = len(pairs)
    max_edges = len(nodes) * (len(nodes) - 1) // 2 # 全连接图的边数
    
    # 防止请求的额外边数超过最大可能的边数
    target_count = min(current_edge_count + extra_edges_count, max_edges)
    
    while len(pairs) < target_count:
        # 随机选两个不同的节点
        u, v = random.sample(nodes, 2)
        pair = tuple(sorted((u, v)))
        
        # 集合会自动去重，如果该边已存在则不会添加
        pairs.add(pair)

    return list(pairs)

# --- 新增功能：连接同一AS内的节点 ---
def connect_nodes_within_as(graph,k=3):
    """
    参数:
    graph (nx.Graph): 包含'router'和'ix'节点的图。
                      'router'节点应有 'type'='router' 和 'as_num' 属性。
    返回:
    nx.Graph: 修改后的原始图对象（添加了AS内部的边）。
    """
    print("\n--- 正在连接同一AS内的节点 ---")
    ix_ix_transit_edges=[]
    # 1. 按AS编号对所有'router'节点进行分组
    as_nodes_map = defaultdict(list)
    node_ix={}
    for node, data in graph.nodes(data=True):
        if data.get('type') == 'router':
            as_num = data.get('as_num')
            if len(graph.neighbors(node))>1:
                print(f"警告：节点 {node} 连接的邻居超过2个，可能数据异常。")
            for nbr in graph.neighbors(node):
                if graph.nodes[nbr].get('type')=='ix':
                    node_ix[node]=nbr
                else:
                    print(f"警告：节点 {node} 的邻居 {nbr} 不是 IX 节点。")
            if as_num is not None:
                as_nodes_map[as_num].append(node)
            else:
                print(f"警告：节点 {node} 类型为 'router' 但缺少 'as_num' 属性。")

    print(f"共找到 {len(as_nodes_map)} 个AS，准备连接内部节点。")

    # 2. 遍历每个AS，连接其内部节点
    total_new_edges = 0
    for as_num, nodes in as_nodes_map.items():
        pairs=generate_connected_pairs(nodes,(k-1)*len(nodes))
        for (n1, n2) in pairs:
            if not graph.has_edge(n1, n2):
                graph.add_edge(n1, n2, relation='internal_as')
                ix_ix_transit_edges.append((node_ix[n1],node_ix[n2],as_num,0))
                total_new_edges += 1
        
            
    print(f"--- AS内部节点连接完成，共添加了 {total_new_edges} 条新边。 ---")
    return graph, ix_ix_transit_edges

def get_all_tuples(filename,as_numbers,ix_nodes_set):
    # 3. 准备一个列表来存储所有最终的四元组
    all_tuples = []

    print(f"--- 开始处理文件: {filename} ---")
    print(f"--- 过滤并变换为四元组... ---")

    try:
        with open(filename, 'r') as f:
            for line_number, line in enumerate(f, 1):
                
                processed_line = line.strip()

                # 过滤 1: 忽略空行
                if not processed_line:
                    continue

                # 过滤 2: 忽略以 '#' 开头的行
                if processed_line.startswith('#'):
                    continue

                # 分割数据
                parts = processed_line.split('|')

                # 检查格式：必须至少有 AS1, AS2, 和一个 loc,rel 对 (即至少3部分)
                if len(parts) < 3:
                    # print(f"警告: 第 {line_number} 行格式不完整，已跳过 -> {processed_line}")
                    continue
                
                asn1 = parts[0]
                asn2 = parts[1]

                # 过滤 3: 检查两个AS编号是否都在 as_numbers 集合中
                if not (asn1 in as_numbers and asn2 in as_numbers):
                    # print(f"信息: 第 {line_number} 行 AS 编号未匹配，已跳过")
                    continue
                    
                # --- 行已通过所有过滤，现在开始变换 ---
                
                # parts[2:] 包含了所有的 "loc,relationship" 字符串
                loc_rel_strings = parts[2:]
                
                # 遍历这个列表中的每一对 loc,rel
                for loc_rel_str in loc_rel_strings:
                    try:
                        # 我们使用 rfind(',') 来查找最后一个逗号
                        # 这可以防止 'Frankfurt Am Main-05-DE,0' 这样的地名被错误分割
                        split_index = loc_rel_str.rfind(',')
                        
                        if split_index == -1:
                            # 没有找到逗号，这个部分格式错误
                            print(f"警告: 第 {line_number} 行数据格式错误 '{loc_rel_str}'，已跳过")
                            continue
                            
                        # 分割
                        location = loc_rel_str[:split_index]
                        relationship = loc_rel_str[split_index+1:]
                        if location not in ix_nodes_set:
                            continue
                        # 创建四元组
                        new_tuple = (asn1, asn2, location, relationship)
                        
                        # 添加到最终列表
                        all_tuples.append(new_tuple)
                        
                    except Exception as e:
                        print(f"警告: 处理 {loc_rel_str} 时出错 (第 {line_number} 行): {e}")


    except FileNotFoundError:
        print(f"\n[错误] 文件未找到: {filename}")
        print("请确保文件和脚本在同一目录下，或者提供完整路径。")
    except Exception as e:
        print(f"\n[错误] 处理文件时发生意外: {e}")


    # 4. 打印最终结果
    print("\n--- 处理完成 ---")
    print(f"总共生成了 {len(all_tuples)} 个四元组。")

    # 打印列表中的前10个元组作为示例
    print("\n--- 列表的前 10 个元组示例: ---")
    for i, t in enumerate(all_tuples[:10]):
        print(f"{i+1}: {t}")

    # 打印最后5个，以供核对
    if len(all_tuples) > 10:
        print("\n--- 列表的最后 5 个元组示例: ---")
        for i, t in enumerate(all_tuples[-5:], start=len(all_tuples)-4):
            print(f"{i}: {t}")
    return all_tuples