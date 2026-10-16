# SEED Emulator Kubernetes 设计

本文以 `seedemu/compiler/Kubernetes.py` 和 `seedemu/k8sTools` 的当前实现为准，说明从 SEED Emulator 编译到 Kubernetes 运行、清理的完整链路。

## 1. 设计结论

- 默认 secondary network 是 **Multus + macvlan + 802.1Q VLAN**；Kube-OVN 仅是可选后端。
- K3s primary CNI 提供 Pod 管理网 `eth0`；AS 内网、IX LAN 等仿真链路由 Multus 以 secondary interface 加入 Pod。
- `compile` 只翻译拓扑，不依赖集群 inventory；`build` 准备 K3s、registry 和跨节点二层 fabric；`up` 完成镜像构建、环境适配和部署。
- 当前没有自研的 Pod 分区算法。编译结果不含 `nodeSelector`、`affinity` 或 `topologySpreadConstraints`，仿真节点最终由 Kubernetes 默认调度器放置。

## 2. 总体架构

```text
SEED Emulator 场景
  -> render
  -> KubernetesCompiler.compile()
       -> k8s.yaml + networking.yaml + images.yaml + Docker contexts
  -> K8sTools.build()
       -> K3s + Multus + registry + L2 fabric
       -> configK3s.yaml + kubeconfig.yaml
  -> K8sTools.up()
       -> preflight -> build/push images -> render kustomization
       -> prepare VLAN parents -> kubectl apply -k -> wait Ready
  -> K8sTools.clean()/down() 或 K8sTools.destroy()
```

三层间通过文件而不是隐式状态耦合：

| 阶段 | 入口 | 主要输入 | 持久输出 |
| --- | --- | --- | --- |
| 编译 | `KubernetesCompiler` | render 后的 Emulator | workload manifest、网络元数据、镜像构建上下文 |
| 集群构建 | `K8sTools.build()` | 带 `kind` 的部署 YAML | `configK3s.yaml`、`kubeconfig.yaml`、可选 inventory |
| 工作负载运行 | `K8sTools.up()` | 上述两类输出 | 集群内资源、`kustomization.yaml` |
| 清理 | `clean/down/destroy` | workload 目录或 `configK3s.yaml` | 删除 workload，或销毁整个环境 |

## 3. 默认 macvlan + VLAN 网络

### 3.1 网络映射

`KubernetesCompiler` 的默认参数是 `cni_type="macvlan"` 和 `macvlan_vlan_mode=True`。每个 SEED Emulator network 被编译为一个 Multus `NetworkAttachmentDefinition`（NAD）：

```text
SEED network N
  -> VLAN ID V
  -> 宿主/虚拟机子接口 <base>.<V>
  -> macvlan(mode=bridge, ipam=static)
  -> Pod secondary interface
```

- 默认 trunk 为 `trunk0`，base interface 为 `ens2`，VLAN 从 100 开始顺序分配。
- Pod 在 Multus annotation 中携带仿真接口的静态 IP/CIDR，不使用集群 IPAM 重新分配。
- NAD annotation 保存 VLAN ID、base interface、trunk 和网络前缀，供运行阶段适配。
- 单个 802.1Q trunk 可用 VLAN ID 为 1..4094。编译器支持配置多个 `macvlan_vlan_trunks` 扩展容量，用尽时直接报错，不会复用 VLAN 破坏隔离。

### 3.2 跨 Kubernetes 节点的二层连通

macvlan 本身不创建跨主机 fabric；所有可能运行同一仿真网络 Pod 的 K3s 节点，必须在相同 VLAN 上二层互通。`build` 根据环境准备 underlay：

- 本地 KVM：默认复用 VM 的 `ens2` 管理网卡承载 VLAN trunk；也可通过 `kvm.extraNetworks` 附加独立二层 NIC。
- 多宿主机 KVM：每个 trunk 在 hypervisor 上对应无 IP libvirt bridge，通过 VXLAN flood domain 延伸到其他 hypervisor，每台 VM 获得一张专用 trunk NIC。
- 物理机：可直接使用已有 VLAN trunk，也可用 `linux-vxlan` 把 bridge 扩展到多台节点。

K3s primary CNI 与仿真网络分离，因此 API、SSH、registry 和健康检查不依赖仿真路由是否收敛。MTU 由部署 YAML 覆盖编译期占位值；经过 VXLAN 时通常使用 1400。

### 3.3 Kube-OVN 可选路径

显式设置 `cni_type="kube-ovn"` 时，编译器输出 `Vpc`、`Subnet` 和 Kube-OVN NAD；`build` 仅在 `fabric.type` 为 `ovn`/`kube-ovn` 时安装 Kube-OVN。该路径适合需要 OVN 逻辑交换机的环境，但额外引入 OVS/OVN controller、NB/SB 数据库和更多 Kubernetes 控制面开销，因此不是当前默认。

## 4. Compile 阶段

### 4.1 处理过程

`KubernetesCompiler._doCompile()` 执行如下转换：

1. 对 Docker 软件依赖分组，创建 namespace。
2. 遍历 registry 中的 `net`，为每个仿真网络生成 NAD 并分配 VLAN。
3. 遍历 `rnode/csnode/hnode/rs/snode`，每个节点生成一个 `replicas: 1` 的 privileged Deployment 和独立 Docker context。
4. 在 Pod annotation 中写入 Multus 网络与静态 IP；在 label/annotation 中保留 ASN、角色、节点名和 Internet Map 元数据。
5. 修补容器启动脚本：按原拓扑重命名网卡、恢复 `tc` 延迟/带宽/丢包、应用 runtime sysctl，并为转发节点关闭 ICMP redirect。
6. 写出 manifest、网络元数据、镜像清单和所需 base-image context。

### 4.2 输出契约

- `k8s.yaml`：macvlan 默认 manifest；Kube-OVN 模式为 `k8s.kube-ovn.yaml`。
- `networking.yaml`：记录 backend、master interface 占位值、MTU、VLAN 模式、trunk 及运行 manifest 名。
- `images.yaml`：记录逻辑镜像名到 Docker context 的映射。
- `<node>/`：每个仿真节点的 Dockerfile 和启动文件。
- `base_images/`：编译器用到的 hash base image context，避免运行阶段误从公网拉取 hash tag。

这些产物不包含真实 registry 地址、K3s 节点 IP 或 Pod 放置，因此同一份编译结果可用于本地 KVM、物理集群和多宿主机 KVM。

## 5. Build 集群阶段

`K8sTools.build()` 由 `seedemu/k8sTools/Runner.py` 编排。入口 YAML 的 `kind` 只表示基础设施归属，网络后端由 `fabric.type` 决定。正式 kind 为 `kvm`、`physical`、`multiHostKvm`；旧的 `*Ovn` 名称仅作兼容别名。

- `kvm`：`PrepareHostAssets` -> `PrepareKvmNetworks` -> `CreateKvmVms` -> `TuneVmLimits` -> `ApplyK3sCluster`。
- `physical`：`PreparePhysicalNodes` -> 可选 Linux VXLAN 配置/验证 -> `ApplyK3sCluster`。
- `multiHostKvm`：`PrepareKvmHypervisors` -> `CreateMultiHostKvmVms` -> 跨宿主机 VLAN fabric 连通和隔离验证 -> `TuneVmLimits` -> `ApplyK3sCluster`。

`ApplyK3sCluster` 的共通流程是：验证 SSH/sudo，通过 Ansible 安装 K3s，在 master 启动私有 registry，准备 SEED base/router 镜像，拉取 kubeconfig，向所有节点预加载 K3s/Multus 镜像，按需安装 Kube-OVN，调优 kubelet/API Server，等待节点和 Multus Ready，最后写出 inventory。

`configK3s.yaml` 是 build 与 up/destroy 的持久契约，包含节点访问方式、registry、CNI/fabric 和销毁元数据；`kubeconfig.yaml` 只负责 Kubernetes API 访问。内部 setup 资源默认复制到临时目录，`--keep-temp` 仅用于调试。

## 6. Up 运行阶段

`K8sTools.up(outputDir, kubeconfig, configK3s)` 依次执行：

1. **Preflight**：验证 manifest/images、kubeconfig、API Server、Node Ready、`kube-system`、namespace 空闲、registry 健康、Docker/buildx 和每个节点到 registry 的连通性。
2. **Build images**：将 compile 输出和 running helper 传到 registry/master 节点；补齐 Dockerfile 的 base image；按 `images.yaml` 逐个执行 `buildx build --load`，再 push 到 `<registry>/<logical-image>`。
3. **Render**：生成 `kustomization.yaml`，将逻辑镜像改写为真实 registry 地址，并用 `configK3s.yaml` 中的 master interface/MTU patch macvlan NAD。
4. **Prepare VLAN**：从 NAD 和 workload annotation 计算所需 `<base>.<VLAN>`，通过本地命令或 SSH 在目标 K3s 节点上创建 802.1Q 子接口。
5. **Deploy**：确保 namespace 存在，执行 `kubectl apply -k <outputDir>`。
6. **Wait**：逐个等待 Deployment rollout，再等待带 `seedemu.io/workload=seedemu` label 的所有 Pod Ready。

`clean()`/`down()` 删除 kustomize 资源和 namespace，保留 K3s、registry 和底层 fabric，用于快速重跑。`destroy()` 先清理 K3s/fabric，再根据 `configK3s.yaml` 中保存的状态删除 KVM 资源；物理机模式不销毁机器。

## 7. 节点分区算法在哪里

需要区分两类“节点”：

### 7.1 K3s VM 节点规划

这部分位于 setup 阶段，不是仿真拓扑分区。

- 单宿主机 KVM：`seedemu/k8sTools/resources/setup/kvm/ManageKvmConfig.py` 中的 `nodes()`/`auto_node()` 按配置生成 master/worker 的名称、IP、MAC 和资源。
- 多宿主机 KVM：`seedemu/k8sTools/resources/setup/multiHostKvm/ManageMultiHostKvmConfig.py` 中的 `vmPlan()` 按 `hypervisors[].vmCount` 遍历分配 VM；master 由 `master.placement` 选定，其余 VM 依次为 worker。

该逻辑是确定性的基础设施规划，不读取 SEED Emulator 的 AS/链路拓扑，也不优化跨主机流量。

### 7.2 仿真 Pod 分区

当前**没有实现这类分区算法**。`Kubernetes.py` 中的 `SchedulingStrategy` 及构造参数只是兼容接口，未参与 manifest 生成；Deployment 不指定 Kubernetes 节点。因此：

- Pod 由 Kubernetes default-scheduler 根据当时可调度条件放置，不保证按 AS 聚合、负载均衡或最小化跨节点链路。
- 未固定的 workload 可在重启后改变位置。
- `ManageK8sManifest.macvlan_vlan_interfaces_by_node()` 能识别 `nodeName`/主机 `nodeSelector`；但当前 workload 未固定，为避免 CNI 因缺少 VLAN parent 失败，它会在所有 K3s 节点上准备相关 VLAN。

## 8. 优化方向

### P0：补齐可控的拓扑分区

保持 compile 的 cluster-agnostic 性，将分区器放在 `k8sTools` 的 render/apply 之间最合适。建议新增独立 placement planner：

1. 从 manifest label/annotation 读取 ASN、role、NAD 和链路关系，从 `configK3s.yaml` 读取节点 CPU/内存/位置。
2. 将 Pod 建模为带资源权重的顶点，共享仿真网络或预估流量建模为带权边。
3. 以“节点容量不超限 + 跨节点边权最小 + 必要的反亲和约束”为目标，先实现可解释的 AS-aware greedy 分区，规模扩大后再接入 METIS/KaHIP 等图分区器。
4. 生成 Kustomize patch，写入 `nodeSelector` 或 required affinity 及 requests/limits，同时输出 placement 报告供复现和调试。

有了确定性 placement 后，VLAN parent 只需在真正承载相关 Pod 的节点上创建，可显著减少网卡数量和启动开销。

### P1：降低大规模构建与发布成本

- 将“每个节点一个镜像”改为少量共享 role/base 镜像 + ConfigMap/volume/init data，减少 build/push 数量和 registry 存储。
- 将当前串行 `buildx build` 改为有界并发或 `buildx bake`，引入 registry cache，并根据 context digest 跳过未变镜像。
- 对 manifest 分批 apply 并控制并发 rollout，避免大量 Deployment 同时创建压垮 API Server、scheduler 和 containerd。
- 为 Deployment 生成合理的 requests/limits；否则 default-scheduler 无法根据真实容量做出可靠决策。

### P1：完善 macvlan/VLAN 生命周期

- 当前编译器可分配多 trunk，但 running 主路径只有全局 `cni.defaultMasterInterface` 覆盖。应让 compile 的 trunk 名与 `fabric.vlanTrunks` 显式对应，按 trunk patch base interface，并在 preflight 检查 VLAN 范围重叠和端到端容量。
- `clean/down` 目前不回收 `up` 创建的 `<base>.<VLAN>` 子接口。应记录运行实例所有权，引用计数后安全删除，避免误删共享 trunk。
- 在 preflight 中增加 base interface、MTU、8021q module、VLAN 透传及同 VLAN 跨节点连通性检查，把 CNI 失败前置到 apply 之前。

### P2：提高可观测性与可恢复性

- 将 compile/build/up 的输出加入 schema version 和兼容性检查，避免新旧 `networking.yaml`/`configK3s.yaml` 混用。
- 持久化 placement、VLAN 分配、镜像 digest 和每阶段状态，使 `up` 可幂等重试、可断点续跑。
- 统一采集 API Server/scheduler 延迟、Pod sandbox/CNI 耗时、镜像 build/pull 命中率和跨节点仿真链路质量，用数据决定并发度和分区参数。

## 9. 用户视角的最小流程

```bash
# 1. 场景脚本内：emu.render(); emu.compile(KubernetesCompiler(...), "output")

# 2. 构建 K3s、registry 和 fabric
python3 -m seedemu.k8sTools build \
  --input configKvmMacvlan.yaml \
  --config-k3s configK3s.yaml \
  --kubeconfig kubeconfig.yaml

# 3. 构建镜像并部署仿真
python3 -m seedemu.k8sTools up -f output -k kubeconfig.yaml -d configK3s.yaml

# 4a. 只清理仿真，保留集群
python3 -m seedemu.k8sTools clean -f output -k kubeconfig.yaml

# 4b. 销毁 K3s/fabric 及由工具创建的 KVM 资源
python3 -m seedemu.k8sTools destroy -d configK3s.yaml
```
