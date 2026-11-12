# k8sTools Setup Resources

这个目录是 `seedemu.k8sTools` 的内部资源目录。用户通常不会直接看到它，因为
`K8sTools.build()` 会把这些资源复制到临时目录中执行，完成后只保留用户指定的
`configK3s.yaml`、`kubeconfig.yaml`，以及可选的 `inventory.yaml`。

所有用户侧和内部操作入口都是 Python 文件。部分复杂系统操作仍保留原 shell
命令序列，但正文内嵌在对应 Python 入口中，不再依赖相邻 `.sh` 资源文件。
这些入口仍会调用系统工具，例如 `virsh`、`docker`、`kubectl`、`ssh`、
`ansible-playbook` 和 `helm`；这些命令才是真正的 KVM、K3s、可选网络
fabric 和镜像操作接口。

## 资源分组

| 路径 | 作用 |
| --- | --- |
| `ApplyK3sCluster.py` | 读取 `configK3s.yaml`，安装或重装 K3s，配置 master registry，导入 bootstrap 镜像，安装 Multus，并在 `fabric.type=ovn` 时调用 Kube-OVN 安装入口。 |
| `DestroyPhysicalCluster.py` | 按 `configK3s.yaml` 清理 K3s、registry、kubeconfig/inventory，并调用对应 fabric 清理入口。 |
| `PreparePhysicalNodes.py` | 已有物理机预检查：验证 SSH、`sudo -n`、基础命令和可选 VXLAN underlay 接口。 |
| `ManageK3sConfig.py` | K3s 阶段 YAML 解析器。负责生成 Ansible inventory、shell 变量、fabric 参数、node-name 和 running 阶段需要的 registry/kubeconfig 信息。 |
| `ansible/k3s-install.yml` | K3s 安装 playbook 模板。它不是运行时生成文件，必须作为资源保留。 |
| `kvm/PrepareHostAssets.py` | 准备 Ubuntu cloud image 和 Docker 镜像 tar 缓存。 |
| `kvm/PrepareKvmNetworks.py` | 单宿主 KVM 前置准备：创建并启动专用管理 NAT 网络，以及 `extraNetworks` 声明的无 IP 二层 trunk 网络。 |
| `kvm/CreateKvmVms.py` | 创建本机 libvirt/KVM VM，生成 `configK3s.yaml` 和 `kvmState.yaml`。 |
| `kvm/TuneVmLimits.py` | 通过 SSH 对 VM 写入文件句柄、netns、邻居表、cni0 hash 等高密度实验限制。 |
| `kvm/DestroyKvmVms.py` | 根据 `kvmState.yaml` 清理 VM、磁盘、cloud-init 和 DHCP reservation。 |
| `kvm/ManageKvmConfig.py` | KVM YAML 解析器，负责避开已有 VM/IP/MAC 冲突并生成 VM 计划。 |
| `multiHostKvm/PrepareKvmHypervisors.py` | 多物理机 KVM 前置准备：验证 hypervisor、创建 routed 管理网络、配置跨 VM subnet 路由；VLAN fabric 还会创建跨宿主 libvirt bridge 和 VXLAN trunk。 |
| `multiHostKvm/CreateMultiHostKvmVms.py` | 在多台 hypervisor 上创建 VM，生成全局 `configK3s.yaml` 和 `multiHostKvmState.yaml`。 |
| `multiHostKvm/ValidateMultiHostKvmFabric.py` | 在 K3s 安装前，对每条 VLAN trunk 执行确定性的跨宿主 VLAN+macvlan 双向连通检查并清理探针接口。 |
| `multiHostKvm/DestroyMultiHostKvmVms.py` | 根据 `multiHostKvmState.yaml` 到每台 hypervisor 清理 VM 和路由/network 状态。 |
| `multiHostKvm/ManageMultiHostKvmConfig.py` | 多物理机 KVM YAML 解析器。 |
| `ovn/InstallKubeOvnFabric.py` | 安装 Kube-OVN non-primary CNI，并把 Kube-OVN/OVS 镜像导入各节点 containerd。 |
| `ovn/ValidateKubeOvnFabric.py` | 验证 Kube-OVN CRD、controller、CNI DaemonSet、OVS/OVN DaemonSet 是否就绪。 |
| `ovn/CleanKubeOvnFabric.py` | 在 K8s API 可用时卸载 Kube-OVN，并清理节点上的 OVN/OVS runtime 文件。 |
| `vxlan/ConfigureLinuxVxlanFabric.py` | 为物理机 macvlan 模式创建 `br-seedemu` 和 VXLAN tunnel。 |
| `vxlan/ValidateLinuxVxlanFabric.py` | 验证 Linux VXLAN bridge 与 macvlan 双向连通；失败时自动调用清理入口。 |
| `vxlan/CleanLinuxVxlanFabric.py` | 删除 Linux VXLAN bridge、VXLAN 和测试 macvlan 接口。 |

运行阶段还会从同级 `resources/running/` 复制并执行
`partitionWorkload.py`。它读取编译器生成的 `k8s.yaml`（或
`k8s.kube-ovn.yaml`）、Kubernetes 节点/Pod API 状态和 ASN 元数据，在镜像
构建前生成 `nodeName` 绑定及 `partitionInput.json`、`partitionApplied.json`
证据。默认算法是 `nodeByAs`；算法参数由 `K8sTools.py up --partition`
传入，只接受 `--partition` 这一种拼写。参数可以是内置算法名，也可以
直接是 `seedemu/k8sTools/` 内的 `.py` 分区脚本路径，脚本通过 `--input/--output` JSON 返回映射，无需
修改框架或注册。接口见 [k8sTools README](../../README.md)。该文件是运行
入口，不是用户输入或持久化配置。

## build 阶段调用关系

`K8sTools.build --input configKvm.yaml` 的核心顺序：

```text
kvm/PrepareHostAssets.py
kvm/PrepareKvmNetworks.py
kvm/CreateKvmVms.py
kvm/TuneVmLimits.py
ApplyK3sCluster.py
[仅 fabric.type=ovn] ovn/InstallKubeOvnFabric.py
```

`K8sTools.build --input configPhysical.yaml` 的核心顺序：

```text
PreparePhysicalNodes.py
ApplyK3sCluster.py
[仅 fabric.type=ovn] ovn/InstallKubeOvnFabric.py
```

`K8sTools.build --input configMultiHostKvm.yaml` 的核心顺序：

```text
multiHostKvm/PrepareKvmHypervisors.py
multiHostKvm/CreateMultiHostKvmVms.py
multiHostKvm/ValidateMultiHostKvmFabric.py
kvm/TuneVmLimits.py
ApplyK3sCluster.py
[仅 fabric.type=ovn] ovn/InstallKubeOvnFabric.py
```

## 关键输入和输出

单宿主 KVM 支持可选 YAML 布尔项 `kvm.freezeGuestUpdates`，默认 `false`。
当设为 `true` 时，`CreateKvmVms.py` 在新 VM 的 cloud-init `bootcmd` 中禁用
APT 周期更新及自动重启，并 mask 自动更新相关 service/timer，避免基准实验中途
升级 systemd 等组件。显式安装依赖仍可执行。该配置只在新 VM 初始化时应用；
修改配置不会改变已经运行的 VM。实验验证器应检查 guest 的实际状态。


VM 资源支持 `master.memoryGiB`、`workers.memoryGiB`，单宿主显式 `nodes[]`
也支持该字段；允许 10.5 等小数，只要能精确转换为整数 MiB。`memoryGb` 是
GiB 的兼容拼写，`memoryMb`/`memory_mb` 保持旧 MiB 语义。多个字段数值冲突、
非正数及无效数值会拒绝。可选的新字段与旧字段择一填写，未填写时保留各 API
原有默认内存；`NormalizeResources.py` 统一转换后，内部 K3s/libvirt 输出仍用 MiB。

| 文件 | 说明 |
| --- | --- |
| 用户输入 YAML | `kind: kvm`、`kind: physical` 或 `kind: multiHostKvm`；`fabric.type` 独立选择网络后端。旧 kind 仅作为兼容别名保留。 |
| `configK3s.yaml` | `build` 的持久输出，也是 `up` 和 `destroy` 的配置来源。 |
| `kubeconfig.yaml` | `build` 的持久输出，供 `kubectl` 和 `up/down` 使用。 |
| `kvmState.yaml` | 临时 KVM 清理状态，会嵌入最终 `configK3s.yaml` 的 `k8sTools.destroy` 元数据中。 |
| `multiHostKvmState.yaml` | 临时多物理机 KVM 清理状态，会嵌入最终 `configK3s.yaml`。 |
| `inventory.yaml` | 可选持久集群 inventory；通过 `K8sTools.py build --inventory inventory.yaml` 写出，包含节点角色、管理 IP 和 CPU/memory/disk 容量。 |

## 手动调试提示

如果需要调试内部资源，优先在 `K8sTools.py build --keep-temp` 失败后进入保留的
临时目录，再执行对应 Python 入口，例如：

```bash
python3 ./kvm/CreateKvmVms.py ./kvm.yaml
python3 ./ApplyK3sCluster.py ./configK3s.yaml
python3 ./ovn/ValidateKubeOvnFabric.py ./configK3s.yaml
```

正常用户流程不需要执行这些内部文件，直接使用例子目录中的 `K8sTools.py build/up/down/destroy`。

单宿主 KVM 的 `kvm.extraNetworks[].workerQueues` 是可选正整数（1..256），
仅用于 `model: virtio`。`ManageKvmConfig.py` 根据 VM 角色生成 vhost 队列参数，
`CreateKvmVms.py` 在创建 worker 时应用；master 和未配置此字段的网络保持原行为。
该值声明设备支持的队列数；实验仍须用 guest `ethtool -l/-L` 验证或选择实际活动队列，
并记录逐队列流量。修改 YAML 不会改变已运行的 VM。
