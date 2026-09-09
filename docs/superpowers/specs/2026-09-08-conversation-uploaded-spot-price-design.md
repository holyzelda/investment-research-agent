# 会话级自定义现货电价设计

## 1. 背景与目标

现有测算链路已经具备现货电价优化能力：

```text
前端问题
  -> POST /ir/chat/diag
  -> 本应用创建/读取 conversation
  -> AI 中台理解参数并调用 create_calculation_task
  -> POST /ir/calc/tasks
  -> ParamAssembler 组装 API_INPUT
  -> 现货电价算法得到 spot_charge_avg / spot_discharge_avg
  -> 飞书副本计算
  -> 保存快照
  -> 前端按 taskId 读取结果快照
```

本需求增加一条可选的自定义电价来源：用户上传一份 Excel，文件只服务于当前会话；同一会话内的所有测算版本均可继续使用该文件，新建会话不继承。

目标如下：

- 文件被选择后立即上传、解析和校验；校验未成功时不能发送问题。
- 不保存原始 Excel，不保存原始 96 点 Blob。
- 上传阶段一次性完成全部支持的 `K` 的 DP 汇总，后续测算只取汇总结果。
- 不让 AI 中台理解、选择或携带文件参数。
- 继续复用既有 `/ir/chat/diag`、`create_calculation_task`、`/ir/calc/tasks`、飞书和快照流程。
- 自定义电价与公共预计算电价严格隔离，不能错误回退或串会话。

## 2. 已确认的现有实现

### 2.1 AI 对话与测算不是同一个接口

`POST /ir/chat/diag` 只负责：

- 创建或读取本应用的 `ir_conversation`；
- 保存用户消息；
- 调用 AI 中台的流式对话接口；
- 透传中台 SSE；
- 记录中台 session id 和最终回答。

它不直接运行飞书测算。

AI 中台在对话过程中根据 `ir_agent.yaml` 调用 `create_calculation_task`，该工具实际请求本应用的 `POST /ir/calc/tasks`。`/ir/calc/tasks` 才会执行 `CalculationTaskService.create_and_run()`，完成参数组装、现货价格获取、飞书计算和快照落库。

### 2.2 现货算法可以复用

领域层已有：

- `day_optimal_by_k()`：对一天的 96 点价格一次构建状态树，并提取多个 `K` 的结果；
- `k_from_inputs()`：按容量、功率和日循环次数计算本次测算所需的 `K`；
- DP 约束：日初不能先放电、充放平衡、最短连续动作、反向切换间隔和循环上限。

公共电价生产路径是：

```text
ir_spot_daily_optimal_province/node/henan
  -> 按 K 和滚动一年窗口求和
  -> sum / slot_count
  -> 应用省级充放电系数
  -> 元/MWh 转元/kWh
```

自定义电价应保持相同的汇总、系数和单位换算口径。

## 3. 产品方案

### 3.1 入口：当前测算输入框附件

不新增全局“电价文件管理”模块。当前需求中的文件不是可跨项目复用的资产，而是当前会话的测算上下文，因此入口放在首页欢迎态和对话态的输入框附近。

用户操作：

```text
选择 Excel 文件
  -> 文件立即上传
  -> 后端解析/校验/DP 汇总
  -> 状态变为“可用”
  -> 用户输入并发送测算问题
```

界面状态至少包括：

- 未选择文件：沿用现有发送流程；
- 上传中/校验中：发送按钮禁用；
- 校验失败：展示原因，不能发送；
- 校验成功：展示文件名、日期范围、有效日数和“本会话测算使用”；
- 替换文件：新文件校验成功后替换当前上下文并清空旧 DP 结果；
- 移除文件：后续测算恢复使用公共电价预计算来源。

校验成功后不自动发起测算，仍由用户明确发送问题。这避免文件上传行为意外触发 AI 或飞书调用。

### 3.2 Excel MVP 格式

MVP 要求一种固定模板，建议使用单 Sheet 长表：

| 日期 | 时点 | 电价（元/MWh） |
| --- | --- | ---: |
| 2025-01-01 | 00:15 | 231.50 |
| 2025-01-01 | 00:30 | 240.20 |
| ... | ... | ... |
| 2025-01-01 | 24:00 | 486.20 |

约束：

- 仅支持 `.xlsx`；
- 每个自然日必须恰好包含 `00:15` 至 `24:00` 共 96 个时点；
- 日期、时点、电价必须可解析；
- 同一自然日重复时点视为该日无效；
- 无效日跳过，但必须在校验结果中统计并展示；
- MVP 一份文件只包含一条电价序列，不在文件内混合多个节点；
- 单价统一为元/MWh，上传时不接受隐式单位猜测；
- 文件大小、行数和总日期范围设置上限，防止异常文件耗尽资源。

后续可以增加 CSV、宽表、双结算价和多节点文件，但不放入第一版协议。

### 3.3 上传后即时校验

增加一个独立的上传预检接口：

```http
POST /ir/calc/spot-context/prepare
Content-Type: multipart/form-data
```

表单字段：

- `file`：Excel 文件；
- `conversation_id`：已有会话时传入，可选；首轮上传为空。

接口职责：

1. 校验当前用户身份和已有会话归属；
2. 校验文件扩展名、大小、Sheet、表头、日期、时点、数值和重复数据；
3. 将有效数据标准化为内存结构 `{business_date: [96 个 Decimal]}`；
4. 对所有支持的 `K` 运行 DP 并聚合；
5. 保存一条临时会话上下文记录；
6. 返回上下文凭证和校验摘要。

没有 `conversation_id` 时，记录先处于待绑定状态，但状态可以直接为 `ready`：它表示“文件已经可用”，不表示已经绑定到某个会话。发送首条问题时再完成一次性绑定。

示例响应：

```json
{
  "contextToken": "opaque-uuid",
  "status": "ready",
  "fileName": "2025年度现货电价.xlsx",
  "validDays": 362,
  "skippedDays": 3,
  "startDate": "2025-01-01",
  "endDate": "2025-12-31",
  "kCount": 19,
  "warnings": ["有3个自然日因时点不完整未参与计算"]
}
```

前端只依据该接口成功响应解锁发送按钮。前端可以做扩展名和大小的快速检查，但不能代替后端校验。

## 4. DP 计算策略

### 4.1 上传时一次性计算全部 K

不保存原始价格点，也不等到用户第一次测算时才计算。上传校验通过后立即计算所有支持的 `K`。

上传路径与现有公共预计算保持同一业务口径：系统仅支持 2 小时或 4 小时，日均充放电次数仅支持 `1.0~2.0`、步长 `0.1`。上传时直接复用现有常量：

```python
k_values = PRECOMPUTE_K_VALUES
```

当前参数字典中的 `daily_cycles` 范围是 `1.0~2.0`、步长 `0.1`，K 的实际计算公式是：

```text
K = min(floor(4 × 日均充放电次数 × 系统时长), 48)
系统时长 = 容量 / 功率
```

由此得到并去重后的完整业务 K 集合共 19 个值：

```text
8, 9, 10, 11, 12, 13, 14, 15, 16,
17, 19, 20, 22, 24, 25, 27, 28, 30, 32
```

`48` 仍是 96 个 15 分钟槽在充放槽数相等约束下的算法理论封顶，但不属于本功能需要穷举的业务集合。现有 `day_optimal_by_k()` 可一次处理上述 19 个 K，内部以最大 K 的状态树提取各个目标 K，不需要执行 19 次相互独立的 DP。

### 4.2 系统时长输入契约

当前 HTTP 归一化代码只校验系统时长大于 0，尚未强制只能取 2 小时或 4 小时。实现本功能时应同步收紧测算主入口，而不能只在上传电价路径中限制：

- 显式传入 `duration_hours` 时，只接受 `2` 或 `4`；
- 传入容量和功率时，先计算 `capacity_mwh / power_mw`，结果必须为 `2` 或 `4`；
- 三项同时传入时，除保持容量、功率、时长一致外，时长仍必须为 `2` 或 `4`；
- 同一会话重算后得到的最终系统时长也必须满足该限制；
- 不合法时在运行现货查询或飞书计算前返回明确的业务校验错误；
- 不允许因 K 不在 19 个值中而静默回退公共电价或返回空电价。

校验浮点推导结果时应使用既有 `math.isclose` 风格的小容差，而不是直接比较浮点数。

### 4.3 保存的结果

每个 `K` 只保存聚合值：

```json
{
  "8": {
    "chargeSum": "12345.600000",
    "dischargeSum": "45678.900000",
    "slotCount": 2896
  },
  "9": {
    "chargeSum": "13501.200000",
    "dischargeSum": "50221.700000",
    "slotCount": 3258
  }
}
```

不保存：

- 原始 Excel；
- 原始 96 点价格 Blob；
- 每天的动作序列；
- 每个时点的明细表。

使用时计算：

```text
raw_avg_charge = chargeSum / slotCount
raw_avg_discharge = dischargeSum / slotCount
spot_charge_avg = raw_avg_charge * charge_factor / 1000
spot_discharge_avg = raw_avg_discharge * discharge_factor / 1000
```

上传文件只包含一条价格序列，因此自定义路径不按节点查询。项目省份和城市/节点仍由正常测算参数处理；省级修正系数在测算时按项目省份应用。

## 5. 单表存储设计

### 5.1 只新增一张表

使用独立的临时上下文表，不复用公共现货表和公共预计算结果表：

```text
ir_conversation_spot_context
```

一条记录代表一份当前有效的上传电价上下文，包含文件摘要和所有 `K` 的聚合结果。

建议字段：

| 字段 | 说明 |
| --- | --- |
| `id` | 上下文 UUID |
| `conversation_id` | 会话 UUID；首轮发送前允许为空，绑定后填写 |
| `user_id` | 上传用户，用于待绑定凭证和归属校验 |
| `status` | `ready`、`replaced`、`expired` 等 |
| `context_token_hash` | 一次性上下文凭证哈希，不保存明文凭证 |
| `file_name` | 原始文件名，仅用于展示 |
| `file_sha256` | 原文件哈希，用于审计和替换识别 |
| `price_unit` | 固定为 `CNY/MWh` |
| `start_date` / `end_date` | 有效日期范围 |
| `valid_day_count` | 有效完整日数 |
| `skipped_day_count` | 跳过日数 |
| `k_results` | JSON，保存 `K -> chargeSum/dischargeSum/slotCount` |
| `algorithm_version` | DP 规则版本 |
| `created_at` / `updated_at` | 创建和更新时间 |
| `last_used_at` | 最近一次参与测算时间 |
| `expires_at` | 临时数据到期时间 |

`conversation_id` 建议建立唯一索引，使一个会话最多一份当前生效上下文。首轮待绑定记录通过哈希凭证和用户 ID 隔离。

### 5.2 为什么不拆明细表

本需求后续测算只需要按 `K` 读取三个聚合值，不需要按日期或时点查询。将原始点位拆成日表、时点表或 DP 日结果表会增加表数量和清理复杂度，不能带来当前产品需要的查询能力。

`k_results` 的规模很小：固定 19 个 `K`，每个只保存两个金额和一个槽数。即使使用 MySQL JSON，也远小于保存全年 96 点原始数据，且一行读取即可完成测算。

### 5.3 替换与历史快照

同一会话重新上传时：

1. 先完整校验并计算新文件；
2. 新文件成功后原子替换当前上下文；
3. 清除旧 `k_results`，写入新文件摘要和新结果；
4. 已完成的 V1/V2 历史快照不改变。

每个成功测算的 `InputSnapshot` 或 `DataSnapshot` 保存来源摘要：

```json
{
  "spotPriceSource": "conversation_upload",
  "spotPriceFileName": "2025年度现货电价.xlsx",
  "spotPriceFileHash": "sha256...",
  "spotPriceValidDays": 362,
  "spotPriceK": 8,
  "spotPriceAlgorithmVersion": "v1"
}
```

历史结果只依赖现有结果快照，不依赖临时上下文是否仍存在。

## 6. 首次测算与会话绑定

### 6.1 首轮没有 conversation_id

当前系统在首条 `/ir/chat/diag` 请求中创建本应用会话。因此上传和首条问题的时序为：

```text
1. 用户选择 Excel
2. POST /ir/calc/spot-context/prepare（无 conversation_id）
3. 后端校验 + 全部 K DP
4. 返回 contextToken，记录 status=ready、conversation_id=NULL
5. 用户输入并点击发送
6. POST /ir/chat/diag，携带 message + contextToken
7. 本应用创建 conversation
8. 在调用 AI 中台前，将上下文绑定到 conversation_id
9. 保存用户消息
10. 调用 AI 中台
11. AI 中台回调 /ir/calc/tasks
12. /ir/calc/tasks 按 conversation_id 读取 ready 上下文
```

`contextToken` 只用于首轮上传记录绑定，不传给 AI 中台，不传给 `create_calculation_task`。

### 6.2 已有会话上传

如果用户已经在会话中：

```text
POST /ir/calc/spot-context/prepare
  -> 直接按 conversation_id 绑定
  -> 后续 /ir/calc/tasks 自动使用新上下文
```

上传接口必须校验会话属于当前用户且未删除。

### 6.3 `/ir/chat/diag` 的最小兼容改动

不把文件传进 `/ir/chat/diag`，因为文件已经在选择时完成校验。该接口仍保持 JSON，只增加一个可选字段：

```json
{
  "message": "测算山西100MW/400MWh储能项目",
  "conversation_id": null,
  "spot_context_token": "opaque-uuid"
}
```

没有该字段的旧请求行为完全不变。

`ChatProxyService.start_chat()` 的正确顺序应调整为：

```text
解析请求
  -> 创建/读取 conversation
  -> 校验并绑定 spot_context_token
  -> 保存用户消息
  -> 获取中台 token
  -> 调用中台
```

文件绑定失败时不能调用 AI 中台，也不能让本次问题看起来已经进入测算。

## 7. `/ir/calc/tasks` 数据源路由

`/ir/calc/tasks` 的外部 JSON 协议和 AI 中台工具参数保持不变。路由逻辑为：

```text
收到真实 HTTP Header: X-IR-Conversation-Id
  -> 校验会话归属
  -> 查询 ir_conversation_spot_context
  -> 找到 status=ready 的当前上下文
       -> 按当前容量/功率/日循环次数计算 K
       -> 从 k_results[K] 读取聚合结果
       -> 应用项目省份系数和元/MWh转元/kWh
  -> 未找到上下文
       -> 继续现有 PrecomputeSpotPriceAlgo
            -> 查询 ir_spot_daily_optimal_province/node/henan
```

伪代码：

```python
context = spot_context_repo.get_ready(conversation_id, user_id)
if context is not None:
    spot_algo = ConversationSpotPriceAlgo(context)
else:
    spot_algo = PrecomputeSpotPriceAlgo(...)
```

当前代码中 `build_task_service()` 在解析 Header 之前调用，未来需要把会话 ID作为构造期上下文传入，或让任务服务通过一个会话感知的现货算法工厂读取上下文。这个调整只影响后端内部装配，不改变 `/ir/calc/tasks` 的调用协议。

### 7.1 不允许静默回退

必须区分：

- 当前会话从未上传自定义电价：走公共预计算；
- 当前会话存在 `ready` 自定义电价：走上传结果；
- 当前会话曾上传但上下文已过期/被清理：阻止需要自定义电价的重算并提示重新上传，不能静默改用公共电价。

为此，历史输入或会话状态需要能识别“本会话曾使用过自定义电价”。如果只保留会话临时表并物理删除记录，删除前应将该状态写入会话元数据，或在任务/快照中结合最近版本来源判断。

## 8. 生命周期与清理

### 8.1 清理时机

- 首轮上传但未发送问题：`expires_at` 短 TTL，例如 30 分钟；
- 当前会话重新上传：新文件校验成功后立即替换旧上下文；
- 用户主动移除：立即删除当前上下文；
- 用户删除会话：同步删除或后台删除绑定上下文；
- 会话长期无活动：定时任务按 `expires_at` 清理；
- 新建会话：不继承旧上下文，但不要求在新会话创建瞬间删除旧会话数据。

“新建会话丢失”是访问隔离语义：新会话的 `conversation_id` 查不到旧上下文。旧会话在删除或到期前仍可打开并继续测算，避免历史会话被打开后突然无法按原口径重算。

### 8.2 临时表不是公共电价库

这张表不参与公共节点列表、不进入公共预计算日更、不被其他用户查询。所有读写都必须同时校验：

```text
conversation_id + 当前 user_id + status=ready
```

## 9. Header 转发验证结论

### 9.1 本应用当前发送方式

当前 `ChatProxyService` 发送给 AI 中台的 `ChatRequest` 是 JSON 请求体，代码形态为：

```python
payload["header"] = {
    "username": quote(user.username, safe=""),
    "userid": user.user_id,
    "X-IR-Conversation-Id": conversation.id,
}
```

随后 `MiddlePlatformHttpClient.stream_chat()` 使用：

```python
client.stream(
    "POST",
    chat_url,
    headers={"Authorization": f"Bearer {access_token}"},
    json=payload,
)
```

因此，`X-IR-Conversation-Id` 在本应用发给中台的第一跳中**不是 HTTP Header**，而是 `ChatRequest.header` JSON 字段。

### 9.2 真实中台接口契约

已于 2026-09-08 读取当前中台实例：

```text
http://internal-3-60.example.invalid:9630/openapi.json
```

该实例公开的 `POST /api/v1/chat/diag` 请求模型 `ChatRequest.header` 的描述明确写明：

> 三方系统自定义请求头，全链路透传至工具调用的后端接口；嵌套结构序列化为紧凑 JSON 字符串注入 HTTP 头，由业务后端自行 JSON 解析。

这不是本应用的推断，而是当前运行中台实例发布的 OpenAPI 契约。由此可以确认当前设计的实际转发机制是：

```text
本应用 ChatRequest JSON.header["X-IR-Conversation-Id"]
  -> 中台读取 ChatRequest.header
  -> 中台将该字段转换为工具回调 HTTP Header
  -> /ir/calc/tasks 读取 Header("X-IR-Conversation-Id")
```

### 9.3 验证边界

仓库和公开 OpenAPI 可以确认：

- 本应用确实把会话 ID放入中台规定的 `header` 字段；
- 当前中台版本的契约明确要求自定义 Header 全链路转发；
- 本应用 `/ir/calc/tasks` 确实读取真实 HTTP Header `X-IR-Conversation-Id`；
- 本应用现有测试已经验证第一跳 payload 中的会话 ID与本应用 conversation 一致。

仓库和公开 OpenAPI 不能单独观察中台到 `/ir/calc/tasks` 的实际线上 HTTP 报文，因为当前中台没有公开 Header echo/debug 接口。上线前建议做一次无副作用联调验收：在测试环境记录或临时回显 `/ir/calc/tasks` 收到的 `X-IR-Conversation-Id`，验证首轮、多轮和两个会话的值分别一致且不串会话。

因此当前结论是：

> **Header 转发机制已经由运行中台的 OpenAPI 契约确认可用；线上报文级验证仍应在测试环境通过中台日志或临时回显完成。它不再是方案设计上的未知依赖，但仍是发布验收项。**

## 10. 实施顺序

1. 固定并发布 Excel 示例模板和校验规则。
2. 新增 `ir_conversation_spot_context` 表及迁移。
3. 收紧测算输入契约，确保容量/功率推导或显式输入的系统时长只能为 2 小时或 4 小时。
4. 实现上传解析器、完整日校验、文件摘要和 19 个业务 `K` 的 DP 聚合。
5. 实现 `spot-context/prepare` 接口、凭证绑定和清理策略。
6. 为 `/ir/chat/diag` 增加可选 `spot_context_token`，确保绑定先于中台调用。
7. 实现会话感知现货算法路由；无上下文继续走 `PrecomputeSpotPriceAlgo`。
8. 在快照中记录自定义电价来源摘要和本次 `K`。
9. 实现前端附件选择、上传状态、失败提示、成功摘要、替换和移除。
10. 增加后端单测、接口测试、DP 聚合一致性测试和前端交互测试。
11. 测试环境完成中台回调 Header 报文级验收。

## 11. 验收标准

- 未上传文件的旧问题流程、AI 工具协议和公共预计算结果不变。
- 所有测算入口只接受最终系统时长为 2 小时或 4 小时的项目，上传路径与公共预计算路径使用同一 19 个 K 集合。
- 文件未校验完成或校验失败时，前端不能发送问题。
- 首轮上传文件后，`/ir/chat/diag` 创建会话并在调用中台前完成绑定。
- AI 中台不需要新增文件参数，仍只调用原 `create_calculation_task`。
- 同一会话 V1、V2、V3 在不同 `K` 下均能正确读取对应的上传汇总结果。
- 新会话不能读取旧会话的自定义电价。
- 自定义上下文不存在时仍使用原公共预计算表；自定义上下文过期时不静默回退。
- 上传表只保存一条会话上下文和小体积 `k_results` JSON，不保存原始 Excel 和原始点位 Blob。
- 历史结果快照可在临时上下文清理后正常展示。
- 测试环境可以证明中台回调 `/ir/calc/tasks` 时收到正确的 `X-IR-Conversation-Id`。
