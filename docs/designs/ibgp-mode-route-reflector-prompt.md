# AS-level iBGP Mode Prompt

**按照以下 Prompt 执行：**

请在 SeedEMU 中把 iBGP 的模式选择和默认 Route Reflector 配置上移到
`AutonomousSystem` 类，而不是继续让 `Ibgp` 层通过是否存在 RR 来推断。

## 目标

在 `AutonomousSystem` 上加入 AS 级别的 `ibgp_mode` 配置，合法值只有：

- `"full-mesh"`
- `"route-reflector"`

默认行为必须保持兼容：没有显式配置时，普通 AS 仍然使用 full mesh。

当用户把某个 AS 设置为 `"route-reflector"`，但没有手动创建 cluster，也没有手动指定
Route Reflector 时，`AutonomousSystem` 必须自动提供：

- 一个确定性的默认 cluster ID。
- 一个确定性的默认 Route Reflector。
- 默认 cluster membership，也就是选中的 RR 作为 reflector，其余 router 作为 client。

但当用户设置多个cluster ID 和 多个Route Reflector的时候 我们必须用joinBgpCluster(),指定好各个router分别都是哪个cluster ID的，不然要报错.

这些默认值和模式决策必须定义在 `AutonomousSystem` 内部，`Ibgp` 层只消费
`AutonomousSystem` 给出的结果并渲染 session。

`__ibgp_mode` 默认使用 `"full-mesh"`。

默认 cluster ID 必须由 AS 决定，不要留在 `Ibgp` 层。使用 ASN 派生的 IPv4 风格
字符串，例如："10.{asn}.0.1"的形式,确保不重复。

默认 Route Reflector 必须由 AS 决定。默认选用在 router 名称升序排序后的第一个 router。


## 背景定位

原先相关代码位置：

- `seedemu/core/AutonomousSystem.py`
  - `createBgpCluster(address)` 注册 RR cluster ID。
  - `_aggregateBgpClusters()` 汇总 cluster、RR、client membership。
  - 目前隐式默认 cluster ID 硬编码为 `"10.0.0.0"`。
- `seedemu/core/Node.py`
  - `Router.makeRouteReflector()` 在 router 上记录是否为 RR。
  - `Router.joinBgpCluster(cluster_id)` 在 router 上记录所属 cluster。
- `seedemu/layers/Ibgp.py`
  - `configure()` 当前调用 `asobj._aggregateBgpClusters()`。
  - 当前通过 `has_rr = any(len(rrs) > 0 ...)` 决定使用 RR 还是 full mesh。
  - `_render_rr_mode()` 负责把 RR/client session intent 写入 router。
  - `_render_full_mesh_mode()` 保持旧的 full mesh 行为。
- `seedemu/layers/_bgp_metadata.py`
  - `route_reflector_client` 和 `route_reflector_cluster_id` 是 BGP intent 字段。
  - BIRD 渲染 `rr client` 和 `rr cluster id ...`。
- `seedemu/layers/Routing.py`
  - FRR 渲染 `bgp cluster-id ...` 和 `neighbor ... route-reflector-client`。

## 行为要求

已有调用`createBgpCluster()`、`joinBgpCluster()`、`makeRouteReflector()` 的旧 RR 用法不能被破坏。

`setIbgpMode()` 必须校验输入，非法值直接抛出`ValueError` 或 `AssertionError`，错误信息要包含合法值。

1. `Ibgp.configure()` 不再用 `has_rr` 自己推断模式。
2. `Ibgp.configure()` 应当从 `AutonomousSystem` 获取 effective iBGP mode：
   - `"full-mesh"` 调用 `_render_full_mesh_mode()`。
   - `"route-reflector"` 调用 `_render_rr_mode()`。
3. RR cluster 聚合、默认 cluster ID、默认 RR 选择都在 `AutonomousSystem` 中完成。
4. AS 的 effective mode 进入 `"route-reflector"`,用户必须显示调用`setIbgpMode("route-reflector")`,然后才可以去调用以下的代码：
   - `createBgpCluster()`。
   - `makeRouteReflector(True)`。
   - `joinBgpCluster(cluster_id)`。
5. 如果用户显式设置 `"full-mesh"`，应优先尊重该设置，除非已经存在 RR 专用配置。
   遇到冲突时不要静默忽略，应该抛出清晰错误，例如：
   `"AS2 has route-reflector cluster/router configuration but ibgp_mode is full-mesh"`。
6. 多 cluster RR 仍然必须校验每个 cluster 有 RR 和 client。默认 RR 只用于用户选择
   `"route-reflector"` 且没有任何 RR 配置的情况。
7. 不要改变 `_bgp_metadata.py` 的 intent schema，继续使用现有字段
   `route_reflector_client` 和 `route_reflector_cluster_id`。
8. 不要改变 BIRD/FRR 渲染语义。BIRD 仍由 `_bgp_metadata.py` 渲染 RR 配置，FRR 仍由
   `Routing.py` 渲染 cluster-id 和 route-reflector-client。
