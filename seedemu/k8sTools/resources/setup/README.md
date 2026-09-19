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
| `applyK3sCluster.py` | 读取 `configK3s.yaml`，安装或重装 K3s，配置 master registry，导入 bootstrap 镜像，安装 Multus，并在 `fabric.type=ovn` 时调用 Kube-OVN 安装入口。 |
| `destroyPhysicalCluster.py` | 按 `configK3s.yaml` 清理 K3s、registry、kubeconfig/inventory，并调用对应 fabric 清理入口。 |
| `preparePhysicalNodes.py` | 已有物理机预检查：验证 SSH、`sudo -n`、基础命令和可选 VXLAN underlay 接口。 |
| `manageK3sConfig.py` | K3s 阶段 YAML 解析器。负责生成 Ansible inventory、shell 变量、fabric 参数、node-name 和 running 阶段需要的 registry/kubeconfig 信息。 |
| `normalizeResources.py` | 共享资源单位转换库；把 `memoryGiB`/`memoryGb` 等输入规范化为内部使用的 MiB。 |
| `ansible/k3s-install.yml` | K3s 安装 playbook 模板。它不是运行时生成文件，必须作为资源保留。 |
| `kvm/prepareHostAssets.py` | 准备 Ubuntu cloud image 和 Docker 镜像 tar 缓存。 |
| `kvm/prepareKvmNetworks.py` | 单宿主 KVM 前置准备：创建并启动专用管理 NAT 网络，以及 `extraNetworks` 声明的无 IP 二层 trunk 网络。 |
| `kvm/createKvmVms.py` | 创建本机 libvirt/KVM VM，生成 `configK3s.yaml` 和 `kvmState.yaml`。 |
| `kvm/tuneVmLimits.py` | 通过 SSH 对 VM 写入文件句柄、netns、邻居表、cni0 hash 等高密度实验限制。 |
| `kvm/destroyKvmVms.py` | 根据 `kvmState.yaml` 清理 VM、磁盘、cloud-init 和 DHCP reservation。 |
| `kvm/manageKvmConfig.py` | KVM YAML 解析器，负责避开已有 VM/IP/MAC 冲突并生成 VM 计划。 |
| `multiHostKvm/prepareKvmHypervisors.py` | 多物理机 KVM 前置准备：验证 hypervisor、创建 routed 管理网络、配置跨 VM subnet 路由；VLAN fabric 还会创建跨宿主 libvirt bridge 和 VXLAN trunk。 |
| `multiHostKvm/createMultiHostKvmVms.py` | 在多台 hypervisor 上创建 VM，生成全局 `configK3s.yaml` 和 `multiHostKvmState.yaml`。 |
| `multiHostKvm/validateMultiHostKvmFabric.py` | 在 K3s 安装前，对每条 VLAN trunk 执行确定性的跨宿主 VLAN+macvlan 双向连通检查并清理探针接口。 |
| `multiHostKvm/destroyMultiHostKvmVms.py` | 根据 `multiHostKvmState.yaml` 到每台 hypervisor 清理 VM 和路由/network 状态。 |
| `multiHostKvm/manageMultiHostKvmConfig.py` | 多物理机 KVM YAML 解析器。 |
| `ovn/installKubeOvnFabric.py` | 安装 Kube-OVN non-primary CNI，并把 Kube-OVN/OVS 镜像导入各节点 containerd。 |
| `ovn/validateKubeOvnFabric.py` | 验证 Kube-OVN CRD、controller、CNI DaemonSet、OVS/OVN DaemonSet 是否就绪。 |
| `ovn/cleanKubeOvnFabric.py` | 在 K8s API 可用时卸载 Kube-OVN，并清理节点上的 OVN/OVS runtime 文件。 |
| `vxlan/configureLinuxVxlanFabric.py` | 为物理机 macvlan 模式创建 `br-seedemu` 和 VXLAN tunnel。 |
| `vxlan/validateLinuxVxlanFabric.py` | 验证 Linux VXLAN bridge 与 macvlan 双向连通；失败时自动调用清理入口。 |
| `vxlan/cleanLinuxVxlanFabric.py` | 删除 Linux VXLAN bridge、VXLAN 和测试 macvlan 接口。 |

## build 阶段调用关系

`K8sTools.build --input configKvm.yaml` 的核心顺序：

```text
kvm/prepareHostAssets.py
kvm/prepareKvmNetworks.py
kvm/createKvmVms.py
kvm/tuneVmLimits.py
applyK3sCluster.py
[仅 fabric.type=ovn] ovn/installKubeOvnFabric.py
```

`K8sTools.build --input configPhysical.yaml` 的核心顺序：

```text
preparePhysicalNodes.py
applyK3sCluster.py
[仅 fabric.type=ovn] ovn/installKubeOvnFabric.py
```

`K8sTools.build --input configMultiHostKvm.yaml` 的核心顺序：

```text
multiHostKvm/prepareKvmHypervisors.py
multiHostKvm/createMultiHostKvmVms.py
multiHostKvm/validateMultiHostKvmFabric.py
kvm/tuneVmLimits.py
applyK3sCluster.py
[仅 fabric.type=ovn] ovn/installKubeOvnFabric.py
```

## 关键输入和输出

VM 资源支持 `master.memoryGiB`、`workers.memoryGiB`，单宿主显式 `nodes[]`
也支持该字段；允许 10.5 等小数，只要能精确转换为整数 MiB。`memoryGb` 是
GiB 的兼容拼写，`memoryMb`/`memory_mb` 保持旧 MiB 语义。多个字段数值冲突、
非正数及无效数值会拒绝。可选的新字段与旧字段择一填写，未填写时保留各 API
原有默认内存；`normalizeResources.py` 统一转换后，内部 K3s/libvirt 输出仍用 MiB。

| 文件 | 说明 |
| --- | --- |
| 用户输入 YAML | `kind: kvm`、`kind: physical` 或 `kind: multiHostKvm`；`fabric.type` 独立选择网络后端。旧 kind 仅作为兼容别名保留。 |
| `configK3s.yaml` | `build` 的持久输出，也是 `up` 和 `destroy` 的配置来源。 |
| `kubeconfig.yaml` | `build` 的持久输出，供 `kubectl` 和 `up/down` 使用。 |
| `kvmState.yaml` | 临时 KVM 清理状态，会嵌入最终 `configK3s.yaml` 的 `k8sTools.destroy` 元数据中。 |
| `multiHostKvmState.yaml` | 临时多物理机 KVM 清理状态，会嵌入最终 `configK3s.yaml`。 |
| `inventory.yaml` | 可选持久集群 inventory；通过 `k8sTools.py build --inventory inventory.yaml` 写出，包含节点角色、管理 IP 和 CPU/memory/disk 容量。 |

## 手动调试提示

如果需要调试内部资源，优先在 `k8sTools.py build --keep-temp` 失败后进入保留的
临时目录，再执行对应 Python 入口，例如：

```bash
python3 ./kvm/createKvmVms.py ./kvm.yaml
python3 ./applyK3sCluster.py ./configK3s.yaml
python3 ./ovn/validateKubeOvnFabric.py ./configK3s.yaml
```

正常用户流程不需要执行这些内部文件，直接使用例子目录中的 `k8sTools.py build/up/down/destroy`。
