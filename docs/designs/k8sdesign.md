# SeedEMU Kubernetes Design

本文总结 `seedemu/compiler/kubernetes.py`、`seedemu/k8sTools` 和
`examples/internet/b61_k8s_compile` 中 native Kubernetes 工作流的高层设计。

## Design Goal

SeedEMU 的 Kubernetes 后端目标不是把现有 Docker Compose 输出简单搬到
Kubernetes 上，而是把已经 render 完成的 SeedEMU emulation 映射成一组可由
Kubernetes 调度、由 Multus 连接多张网卡、能在多机上进行部署，目的是为了突破单机规模限制的仿真网络。

核心设计理念是分层解耦：

- `compile` 只把仿真网络映射成k8s可读的manifest文件。只关心把 SeedEMU 的节点、网络和镜像构建上下文翻译成 Kubernetes
  资源，不依赖真实集群、节点 inventory 或调度位置。
- `build cluster` 只关心准备可运行这些资源的 K3s 集群、registry 和网络
  fabric，不重新解释 SeedEMU 拓扑。
- `running` 只负责在建好的集群上部署我们compile产生的manifest文件。

这种分层让同一份 compile 输出可以在本机 KVM、已有物理机、多物理机 KVM 等
不同底座上部署，也让集群准备和 workload 发布可以独立调试、清理和重跑。

## Networking Model

Kubernetes 集群网络和 SeedEMU 模拟网络被明确分开。

K3s 自身的 primary CNI 负责 pod 的基础管理网络，也就是容器默认的 `eth0`。
SeedEMU 里的 AS 内网、IX peering LAN 等模拟链路通过 Multus 作为 secondary
interfaces 附加到 pod 上。这样每个 SeedEMU node 在 Kubernetes 中通常是一个
privileged Deployment，而它连接的每条 SeedEMU 网络对应一个 Multus
`NetworkAttachmentDefinition`。

默认设计走 Kube-OVN/OVS：OVS/OVN 提供跨节点的 secondary network dataplane，从而提供了多机的K8S仿真。

OVN+OVS 的边界则是“真实性优先”：当实验必须保证每个 IX、AS 内部 LAN 或其他仿真链路都是独立逻辑交换机，需要跨节点保持同一二层网络、支持重叠地址或严格阻止网络间泄漏时，应使用 OVN+OVS。

这也是当前 B61 示例和 `k8sTools build` 三个公开入口的主路径：local KVM、
physical nodes、multi-host KVM 最终都准备 K3s + Multus + Kube-OVN/OVS。

macvlan 是可选支持方向，而不是默认路径。编译器可以输出 macvlan NAD，running
阶段也能按 macvlan backend 渲染 kustomization 和必要的 CNI 信息。macvlan
更接近 Linux 原生二层数据面，适合已有 underlay 二层连通或显式准备 bridge /
VXLAN fabric 的环境，但是由于OVN+OVS为过于追求真实性,从而会导致在大规模时用它会导致创建pod对象的时候很慢而且很容易让API Server，还包括 Kube-OVN Controller、OVN NB/SB 数据库、各节点 ovn-controller、ovs-vswitchd 并发过高导致问题；但我们使用macvlan+vlan的设计的时候,802.1Q VLAN ID 只有 1..4094，也就是最多支持4094个网络;下一步需要实现 Q-in-Q、多个 underlay trunk，或拆分 fabric。

它对宿主机网络条件更敏感，因此默认设计仍以
Kube-OVN/OVS 为稳定基线。

## Compile Contract

Compile 阶段由 `KubernetesCompiler` 完成。它输入的是已经 render 完成的
SeedEMU `Emulator`，输出的是一个 cluster-agnostic 的 Kubernetes workload
目录。

输出包括：

- 一个 Kubernetes manifest：默认是 `k8s.kube-ovn.yaml`，macvlan 模式下是
  `k8s.yaml`。
- `images.yaml`，描述逻辑镜像名和每个节点的 Docker build context。
- 每个 SeedEMU node 对应的 Docker build context。
- 必要时附带 base image context，供后续 build 阶段稳定构建。

B61 示例中的 `mini_internet_k8s.py` ：构造 mini-Internet，
render 后调用 `KubernetesCompiler`，默认输出到 `./output`。用户可以选择默认
Kube-OVN 输出，也可以显式选择 macvlan 输出。

## Build Cluster Contract

Build cluster 阶段由 `K8sTools.build()` 统一入口驱动。用户
提供一个带 `kind` 的 YAML，工具根据 kind 选择底座准备方式，并把内部 setup
资源复制到临时目录执行。正常情况下，用户目录只保留生成的 `configK3s.yaml`、
`kubeconfig.yaml` 和可选 inventory。

当前公开的 build kind 有三类：

- `kvmOvn`：在本机 libvirt/KVM 上创建 VM，再在这些 VM 上构建 K3s。
- `physicalOvn`：使用已有物理节点，直接在这些节点上构建 K3s。
- `multiHostKvmOvn`：在多台物理 hypervisor 上创建 KVM VM，并组成同一个 K3s
  集群。

无论底座不同，build 流程是一致的：

1. 解析用户 YAML，规范所需内容。
2. 如果需要 VM，则先准备 KVM 宿主机资源并创建 VM；如果是物理机，则做节点
   连通性和权限预检查。
3. 生成安装 K3s 所需的文件。
4. 安装 K3s。
5. 在 master 上准备 registry，并进行配置。
6. 安装 Multus 和 Kube-OVN/OVS(额外组件)。
7. 对节点做面向大规模网络仿真的系统和 K3s 调优。
8. 验证是否安装就绪。
9. 写出稳定的 `configK3s.yaml`、`kubeconfig.yaml` 和可选 inventory。

`configK3s.yaml` 是 build 和后续阶段之间的主要持久契约。它不仅描述 K3s 节点
和 registry，也保存 `k8sTools` 后续 destroy 所需的元数据。这样 `destroy` 可以清理干净相应的资源。
而`kubeconfig.yaml`则被用于访问k8s API.后续running部分都要用到它。

## Running Contract

Running 阶段由 `K8sTools.up()` 驱动，输入是 compile 输出目录、`kubeconfig.yaml`
和 `configK3s.yaml`。它的职责是把逻辑 workload 变成一个真实集群上的运行实例。

高层流程如下：

1. 检查 compile 输出是否完整，并确认前期状态。
2. 从 `images.yaml` 读取逻辑镜像列表,将 compile 输出发送到 master 所在节点，在那里 build images，并 push 到 registry。
3. 渲染 `kustomization.yaml`，把逻辑镜像名改写为真实 registry 地址。
4. 使用 `kubectl apply -k` 部署。
5. 等待 ready。

`K8sTools.down()` 只删除 namespace及相关仿真资源，保留物理环境，适合修改 compile 输出后快速重跑。
`K8sTools.destroy()` 则是基于 `configK3s.yaml` 中的元数据清理K8S配置.

## Lifecycle Summary

完整用户流程可以理解为四个边界清晰的阶段：

```text
SeedEMU scenario
  -> compile to Kubernetes emulator-network
  -> build cluster and network fabric
  -> up emulator-network on the cluster
  -> clean emulator-network or destroy infrastructure
```
