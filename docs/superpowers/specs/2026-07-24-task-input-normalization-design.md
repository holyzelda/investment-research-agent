# 测算任务输入归一化设计

日期：2026-07-24  
状态：已确认，待审阅  
范围：仅升级既有 `POST /ir/calc/tasks` 的 HTTP 输入边界，以匹配 `agent-backend/ir-agent.yaml` 中的中台工具声明。

## 目标

中台已经能够从自然语言中提取容量、功率、系统时长等原始参数，但暂不负责规模换算。既有 `POST /ir/calc/tasks` 仅强制接收 `capacity_mwh` 和 `power_mw`，无法处理“100MW 2H”“200MWh 2H”或“仅 2H 系统”。

本设计不增加新 URL；扩展既有接口，使它在 HTTP 层接受 `capacity_mwh`、`power_mw`、`duration_hours` 的有效组合，并在进入测算领域前归一化为既有的容量和功率。

## 请求契约

接口保持：

```http
POST /ir/calc/tasks
```

### 固定必填字段

```json
{
  "province": "甘肃"
}
```

`province` 始终必填。

### 条件必填的规模字段

以下三项均为可选正数，但请求必须满足一个有效组合：

- `capacity_mwh`：容量，MWh；
- `power_mw`：功率，MW；
- `duration_hours`：系统时长，小时，仅用于请求归一化。

| 输入 | 归一化结果 |
| --- | --- |
| `power_mw + capacity_mwh` | 直接使用 |
| `power_mw + duration_hours` | `capacity_mwh = power_mw × duration_hours` |
| `capacity_mwh + duration_hours` | `power_mw = capacity_mwh ÷ duration_hours` |
| 仅 `duration_hours` | 默认 `power_mw = 100`，再推导容量 |
| 三项都有且一致 | 使用显式 `capacity_mwh`、`power_mw` |
| 三项都有但不一致 | HTTP 400 |
| 仅 `power_mw`、仅 `capacity_mwh` 或三项皆无 | HTTP 400 |

所有传入数值均必须大于 0。三项同时传入时，以 `capacity_mwh == power_mw × duration_hours` 为一致性规则，使用严格的小数容差校验，避免浮点表示误差误判。

### 可选基础字段

| 字段 | 规则 |
| --- | --- |
| `node_name` | 可选；保留现有节点校验和省级回退逻辑。 |
| `voltage_kv` | 可选，默认 `220`，只接受 `110`、`220`。 |
| `conversation_id` | 对中台工具调用必须提供；保留既有兼容语义：直调省略时由后端创建新会话。已有 ID 必须属于当前用户且未软删除，否则 404。 |

### 参数字典覆盖

`param_overrides` 保持现有对象结构。中台第一期只使用其中的 `operation_years`：

```json
{
  "param_overrides": {
    "operation_years": 20
  }
}
```

它不变为顶层字段，原因是 `operation_years` 已是参数字典控制的受控输入。未传时沿用参数字典默认 `15`，只允许 `15`、`20`；它只选择对应的飞书模板，不写入飞书 `API_INPUT`。

## 示例请求

容量和功率：

```json
{
  "province": "甘肃",
  "power_mw": 100,
  "capacity_mwh": 200,
  "conversation_id": 42
}
```

功率和时长：

```json
{
  "province": "甘肃",
  "power_mw": 100,
  "duration_hours": 2,
  "conversation_id": 42
}
```

容量和时长：

```json
{
  "province": "甘肃",
  "capacity_mwh": 200,
  "duration_hours": 2,
  "conversation_id": 42
}
```

只有时长及明确运营期：

```json
{
  "province": "甘肃",
  "duration_hours": 2,
  "conversation_id": 42,
  "param_overrides": {
    "operation_years": 20
  }
}
```

最后一个请求进入既有测算服务前会归一化为 `power_mw=100`、`capacity_mwh=200`。

## 实现边界

在 calculation interface/application 边界新增一个纯归一化函数：

```python
normalize_project_basics(
    province=...,
    capacity_mwh=...,
    power_mw=...,
    duration_hours=...,
    node_name=...,
    voltage_kv=...,
) -> ProjectBasics
```

`TaskCreateReq` 允许三个规模字段为空；路由在调用 `CalculationTaskService.create_and_run()` 前调用归一化函数。任务服务继续只收到现有 `ProjectBasics`：

```python
ProjectBasics(
    province=...,
    capacity_mwh=...,
    power_mw=...,
    node_name=...,
    voltage_kv=...,
)
```

因此不改动：

- `ProjectBasics`；
- `CalculationTaskService`；
- `ParamAssembler`；
- 参数字典；
- 飞书 `API_INPUT` 写入；
- 飞书模板选择；
- `api_input`、`input_snapshot`、`report_snapshot`；
- 已有任务、结果和报告响应契约。

`duration_hours` 仅存在于 HTTP 请求到 `ProjectBasics` 的转换过程中，不会写入参数字典、`api_input`、输入快照、飞书接口区或报告快照。

## 错误与兼容性

- 请求结构或给定数值不合法：沿用全局异常处理，HTTP 400 `{code,msg,data}`；
- 规模组合不足或不一致：归一化函数抛出 `ValidationException`，HTTP 400；
- 会话不存在、非本人或已软删除：沿用既有任务服务，HTTP 404；
- 既有 `province + capacity_mwh + power_mw` 调用保持完全兼容；
- `answer.data.biz` 中的任务成功/失败响应仍是当前 `/ir/calc/tasks` 的完整响应壳。

## 测试

新增纯函数单测，覆盖：

1. 现有容量+功率直通；
2. 功率+时长推导容量；
3. 容量+时长推导功率；
4. 仅时长采用 100MW 默认；
5. 三项一致；
6. 三项不一致；
7. 仅功率、仅容量、三项皆无。

扩展既有任务 API 测试，验证 `duration_hours` 请求成功后，冻结输入中仅包含归一化后的 `power_mw`、`capacity_mwh`，不出现 `duration_hours`。
