# SEED Emulator KubeVirt Hybrid Kubernetes 设计文档

## 1. 概述 (Overview)

本设计旨在扩展 SEED Emulator，使其能够利用 **KubeVirt** 在 Kubernetes 集群中运行虚拟机（VM）节点，同时保持与容器节点的互操作性。目标是覆盖本地开发环境与标准 Linux 服务器环境。

### 核心目标
1. **高保真仿真**: 允许特定节点运行自定义内核或容器之外的操作系统能力。
2. **混合部署**: 在同一仿真网络中混合运行容器（Docker）和虚拟机（KubeVirt）。
3. **无缝集成**: 保持 Python 拓扑定义方式不变，通过 `node.setVirtualizationMode('KubeVirt')` 启用 VM。
4. **自动化部署**: 提供一键脚本搭建 Kind + Multus + KubeVirt 环境。

## 2. 架构设计 (Architecture)

### 2.1 基础架构层 (Infrastructure)
- **宿主机**: Linux 开发机 / Linux 服务器。
- **集群管理**: **Kind (Kubernetes in Docker)**。
- **虚拟化技术**: **KubeVirt**，优先 KVM；无硬件虚拟化时可用 QEMU 软件模拟（性能较低）。
- **网络层**: **Multus CNI**，使 Pod/VM 可挂载多网卡（eth0 管理网，net1/net2 仿真网）。

### 2.2 节点类型 (Node Types)

| 特性 | 容器节点 (Container Node) | 虚拟机节点 (KubeVirt Node) |
|:---|:---|:---|
| **资源定义** | Kubernetes `Deployment` | KubeVirt `VirtualMachine` |
| **启动方式** | Docker 镜像启动 | ContainerDisk + Cloud-Init |
| **配置注入** | `Dockerfile` 构建时注入 + 启动脚本 | `Cloud-Init` (User Data) 运行时注入 |
| **IP 管理** | `replace_address.sh` (容器内执行) | `write_files` + `runcmd` (Cloud-Init) |
| **适用场景** | 路由器、Web、普通主机 | 自定义内核测试、特殊网络栈、高隔离需求 |

## 3. 动态注入策略 (Dynamic Injection Strategy)

SEED Emulator 传统上依赖 `Dockerfile` 构建镜像。对于 VM 路径，应避免构建体积巨大的 VM 镜像。

**方案**: 使用通用 Cloud Image（如 Ubuntu）+ Cloud-Init。

### 3.1 转换逻辑
编译器 `Kubernetes.py` 进行如下转换：

1. **基础镜像**
   - 容器: `FROM ubuntu:20.04`
   - VM: `quay.io/containerdisks/ubuntu:22.04`

2. **文件注入 (`node.addFile`)**
   - 容器: `COPY file /path/file`
   - VM: 转换为 Cloud-Init `write_files`

3. **软件安装 (`node.addSoftware`)**
   - 容器: `RUN apt-get install -y package`
   - VM: 转换为 Cloud-Init `packages`

4. **启动命令 (`node.appendStartCommand`)**
   - 容器: 写入 `/start.sh` 并作为 CMD 执行
   - VM: 转换为 Cloud-Init `runcmd`

## 4. 网络与地址管理 (Networking & Address Hack)

SEED Emulator 采用静态 IP，和 CNI 动态 IPAM 存在冲突。

### 4.1 容器方案
- Multus 创建接口后，容器内执行 `/replace_address.sh`，通过 `ip addr add` 覆盖地址。
- 接口名通常为 `net1`, `net2`。

### 4.2 虚拟机方案
- VM 内常见接口顺序：`eth0`（管理网）、`eth1`、`eth2`（仿真网）。
- 编译器按接口顺序生成 Cloud-Init 配置，将模型中的网卡映射到 VM 内设备名。

关键约束：
- 必须保证 Multus CNI 配置与二层互通能力正确（`bridge`/`macvlan` 等）。
- 在 Kind 本地验证中，`bridge` 模式最稳健。

## 5. 实施计划 (Implementation Plan)

1. **Python 核心扩展**
   - `Node.py`: 增加 `virtualization_mode` 属性。
   - `Kubernetes.py`: 增加 `_compileNodeKubeVirt`，生成 Cloud-Init 与 VM 清单。

2. **环境脚本**
   - `setup_kubevirt_cluster.sh`
   - 检测 CPU 虚拟化能力。
   - 安装 Kind、Multus、KubeVirt。
   - 等待组件就绪并输出诊断信息。

3. **验证**
   - 构建“1 VM 路由器 + 2 容器主机”拓扑。
   - 验证互通、BGP、恢复能力。
