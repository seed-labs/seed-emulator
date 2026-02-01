# SEED-Emulator Kubernetes Examples

本目录包含将 SEED-Emulator 部署到 Kubernetes 的示例脚本。

## 示例对照表

| K8s 示例 | 对应 Docker 示例 | 说明 |
|:---|:---|:---|
| `k8s_simple_as.py` | `basic/A00_simple_as` | 最简单的 2 AS + 1 IX 拓扑 |
| `k8s_transit_as.py` | `basic/A01_transit_as` | Transit AS 拓扑示例 |
| `k8s_nano_internet.py` | `basic/A20_nano_internet` | 小型互联网仿真 |
| `k8s_mini_internet.py` | `internet/B00_mini_internet` | 完整的小型互联网 |
| `k8s_multinode_demo.py` | (新增) | 展示多机调度、资源限制等 K8s 高级功能 |

## 快速开始

### 1. 环境准备
```bash
# 创建 Kind 集群 (含本地 Registry)
./setup_kind_cluster.sh

# 配置 Registry Mirror
./patch_kind_registry.sh

# 安装 Multus CNI
kubectl apply -f https://raw.githubusercontent.com/k8snetworkplumbingwg/multus-cni/master/deployments/multus-daemonset-thick.yml
```

### 2. 运行示例
```bash
# 编译
PYTHONPATH=../.. python3 k8s_simple_as.py

# 构建并推送镜像
cd output_simple_as && ./build_images.sh

# 部署
kubectl apply -f k8s.yaml

# 验证
kubectl get pods -n seedemu
```

## K8s vs Docker Compose 核心优势

| 能力 | Docker Compose | Kubernetes |
|:---|:---|:---|
| **故障自愈** | ❌ 无 | ✅ Pod 自动重建 |
| **多机扩展** | ❌ 手动 | ✅ 原生支持 |
| **资源调度** | ❌ 无 | ✅ Request/Limit |
| **滚动更新** | ❌ 无 | ✅ 零停机 |

## 文件说明

- `k8s_*.py`: K8s 示例脚本
- `api_server.py`: K8s API 服务 (用于可视化)
- `setup_kind_cluster.sh`: Kind 集群创建脚本
- `patch_kind_registry.sh`: Registry 配置修复脚本
