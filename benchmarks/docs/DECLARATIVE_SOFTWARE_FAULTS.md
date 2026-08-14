# 声明式软件安装与故障扩展

## 目标与边界

`SoftwareSpec v1` 把软件安装、能力发布和故障生成接入现有拓扑—故障闭环：

```text
TopologyRequest.software
        ↓ 严格 schema、包名/路径/目标校验
SoftwareSpec v1
        ↓ SEED addSoftware/setFile
Docker 镜像 + topology_manifest.json
        ↓ 软件/资产/故障画像发现
FaultSpec v1 候选
        ↓ 现有影响、冲突和恢复门禁
安全执行计划 → 快照 → 注入 → 验证 → 恢复
```

“任意软件”在 v1 中表示基础镜像 apt 仓库能够解析的软件包，不包括 URL、
任意 Dockerfile 指令、第三方仓库脚本或宿主机安装。“自动故障”不猜测未知
软件的语义；声明者必须选择一个已审计的类型化 fault profile。能力发现会为
每个目标资产和 profile 自动生成确定性 `FaultSpec`。

## SoftwareSpec v1

声明位于拓扑请求的 `software` 数组。完整可运行输入见
`generator/topology/examples/software_fault_demo.json`。

```json
{
  "software_id": "jq_tools",
  "packages": ["jq"],
  "target_roles": ["host"],
  "target_asns": [64512],
  "target_nodes": ["host0"],
  "capabilities": ["json.query.v1"],
  "managed_files": [
    {"path": "/etc/jq/benchmark.conf", "content": "mode=healthy\n", "mode": "0644"}
  ],
  "fault_profiles": [
    {
      "profile_id": "disable_binary",
      "fault_type": "software.executable.disabled",
      "parameters": {"path": "/usr/bin/jq", "expected_mode": "0755"}
    }
  ]
}
```

编译器只把经过正则校验的包名传给 `addSoftware()`；managed file 只允许写入
`/etc/`、`/opt/benchmark/` 和 `/usr/local/etc/`，并拒绝账户、DNS、shell 和
解释器等受保护路径。目标可以按角色、ASN 和 SEED 节点名做交集选择。

## 软件能力清单

每次新编译的 `topology_manifest.json` 包含：

- `software_capability_schema_version`：当前为 1；
- `software_catalog`：拓扑声明的软件、解析后的支持包、能力和 profile；
- `assets[].software`：该容器实际应具备的软件能力；
- profile 只包含类型化参数，不包含可执行 shell 命令。

旧 topology plan 不含 `software` 时保持原指纹；旧 manifest 也仍能被读取。
重新编译后会发布内置路由器 `iptables` 能力和新的声明能力。

## 内置通用 FaultDriver

### `software.config.replace`

对生成器管理的配置文件做一次精确 UTF-8 文本替换。构建器自动加入
`python3-minimal` 支撑包。驱动在变更前要求健康值恰好出现一次且错误值不
存在；快照只记录 SHA-256；恢复同时接受“仍为故障状态”和“已经恢复状态”，
因此是幂等的。运行时文本采用 Base64 参数传递，不落入宿主 shell。

### `software.executable.disabled`

只允许 `/usr/bin`、`/usr/sbin`、`/usr/local/bin` 和 `/usr/local/sbin` 下的
显式可执行文件。注入前检查声明的健康 mode，然后设置 `000`；恢复为声明
mode。shell、env、python 和系统账户文件均不可作为目标。

现有 `network.acl.scoped` 仍是 iptables 配置错误的更高语义插件；它与上述
通用驱动共享故障编译、资源锁、影响预算、journal 和逆序恢复机制。

## 自动发现与执行

```bash
python3 -m generator.faults.cli discover-software \
  --capabilities benchmarks/generated/declarative/software_fault_demo/output/topology_manifest.json \
  --seed benchmark-seed \
  --output /tmp/software-fault-candidates.json

python3 -m generator.faults.cli compile \
  --spec /tmp/software-fault-candidates.json \
  --capabilities benchmarks/generated/declarative/software_fault_demo/output/topology_manifest.json \
  --relationship independent \
  --output /tmp/software-fault-plan.json

python3 -m generator.faults.cli validate-software \
  --capabilities benchmarks/generated/declarative/software_fault_demo/output/topology_manifest.json \
  --seed benchmark-seed \
  --journal-dir benchmarks/reports/software_fault_demo_journals \
  --output benchmarks/reports/SOFTWARE_FAULT_DEMO_LIFECYCLE.json
```

发现结果以容器、software id、profile id 和拓扑指纹派生稳定 ID。运行仍使用
现有 `inject`/`recover` 子命令，崩溃恢复与审计日志格式不变。
`validate-software` 会对发现的每个 profile 执行真实无 AI 基线、快照、注入、
生效检查、恢复和恢复检查，并生成机器可读证据。

## 扩展新故障语义

新增语义应实现 `FaultDriver`，给出唯一 `fault_type`，然后调用
`register_driver()`。注册器拒绝覆盖现有类型。插件必须：

1. 从 capability manifest 发现目标，而不是猜容器名；
2. 校验 profile 参数的精确 key 集、路径和值域；
3. 产生 snapshot、inject、active check、cleanup；
4. 使用最小资源锁并保持 cleanup 幂等；
5. 不接受 profile 中的任意 shell 命令；
6. 添加编译、冲突、失败恢复和真实无 AI 生命周期测试。

这使软件目录、故障语义和组合策略彼此独立：增加软件通常只需声明；只有
出现新的故障机制时才增加插件，不需要修改故障编译器或执行器。
