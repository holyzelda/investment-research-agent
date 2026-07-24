# 中台测算对接设计

日期：2026-07-23
状态：已确认，待用户审阅
范围：中台自然语言测算闭环的第一阶段；不改变飞书测算、任务快照、结果快照和报告的既有领域契约。

## 目标

用户在首页输入自然语言，本应用后端代理中台 `POST /api/v1/chat/diag`。中台负责意图识别、参数提取、缺项与冲突追问，参数齐备后调用现有 `POST /ir/calc/tasks`。中台将该接口的完整 `{code,msg,data}` 响应置于 SSE `answer.data.biz`，前端复用当前结果、历史和报告展示逻辑。

中台不成为测算结果或报告历史的事实来源；本应用 `conversation_id` 始终是任务、版本、快照、结果和报告的唯一历史入口。

## 调用边界

```text
前端
  -> POST /ir/chat/diag {message, conversation_id|null}
  -> userId / username 仍由既有请求拦截器附带

本应用后端
  -> 首条消息创建 ir_conversation
  -> 从 application.yml / Nacos 读取中台配置
  -> 换取或复用中台 access token
  -> 调用 POST <middle_platform>/api/v1/chat/diag
  -> 原样转发中台 SSE

中台
  -> 追问并收集测算参数
  -> 调用 POST http://127.0.0.1:9089/ir/calc/tasks
  -> 将 IR 完整响应壳放入 answer.data.biz

既有 IR 测算服务
  -> 飞书副本测算、任务版本、输入/结果快照、报告快照
```

`/ir/calc/tasks` 保留其既有任务、快照、结果和报告行为。中台只是该接口的编排调用方。

## 标识与历史

### 本应用会话

`ir_conversation.id` 即 `conversation_id`，是本应用唯一主会话标识：

- 前端管理和后续请求携带 `conversation_id`；
- 测算任务、版本、结果快照和报告均归属该 ID；
- 打开历史会话时，只读取本应用已有数据，不调用中台；
- 用户在历史会话继续发送消息时，才使用中台续接能力。

点击“新对话”仅清空前端当前会话状态，不立即创建数据库记录。用户发送第一条有效消息时，后端创建会话，并将去首尾空白后的前 30 个 Unicode 字符写入 `title`，不加省略号。

### 中台会话

中台 `session_id` 只用于中台对话上下文续接，不是业务历史主键，前端不保存、不传递、不展示。

在 `ir_conversation` 新增：

```sql
middle_platform_session_id VARCHAR(255) NULL
```

并新增联合唯一索引：

```sql
UNIQUE KEY uq_ir_conversation_user_middle_session
  (user_id, middle_platform_session_id)
```

后端收到中台首轮 `session_id` 后持久化到当前本应用会话。后续请求按 `conversation_id` 查询该值，再传给中台 `/chat/diag`。

- 首轮未收到有效 `session_id`：保留已创建会话，字段保持 `NULL`；用户在同一会话重试时新建中台会话。
- 收到 `session_id` 但保存失败：终止本轮代理流并向前端报告本应用错误，不继续无法恢复的对话。
- 已有非空映射又收到不同 `session_id`：不覆盖，按状态冲突终止本轮。
- 删除本应用会话：只软删除 `ir_conversation`，不级联软删除子表；所有读取任务、结果和报告的接口须经当前用户和未删除会话过滤。中台外部会话由中台过期策略处理，本应用不主动删除。

## 前端到后端代理

新增接口：

```http
POST /ir/chat/diag
Content-Type: application/json
Accept: text/event-stream
```

请求体：

```json
{
  "message": "帮我测算广东 100MW/200MWh 储能项目",
  "conversation_id": null
}
```

校验：

- `message` 去首尾空白后长度必须为 1–2000；
- `conversation_id` 可为 `null`；非空时为正整数，且必须属于当前用户、未软删除；不满足归属或状态时统一 404；
- 参数结构或业务校验不合法遵循项目统一 HTTP 400 `{code,msg,data}`。

首轮创建会话后，代理 HTTP 响应头返回：

```http
X-IR-Conversation-Id: <conversation_id>
```

前端以流式 `fetch` 读取该响应头后写入既有 `calculation.conversationId`，再消费 SSE。后端 CORS 暴露 `X-IR-Conversation-Id`，确保前后端端口或域名不同的浏览器部署也可读取该头。

中台 SSE 的事件、`id`、`data` 和语义全部原样透传；本应用不改写或重新定义中台 SSE。

## 身份与中台认证

现有 IR 业务接口仍强制要求：

```http
userId: <非空用户 ID>
username: <URL 编码的非空用户名>
```

缺任一个，后端返回 HTTP 401：

```json
{"code":401,"msg":"未获取到平台用户身份","data":null}
```

后端调用中台 `/chat/diag` 时：

- 从当前 IR 请求身份获得用户信息；
- 传递中台要求的 `end_user_id`、`end_user_name`；
- 传递中台新增的 `header` JSON，其中包含 `userId`、URL 编码后的 `username`；
- 中台负责将该 JSON 中的信息写入工具 HTTP Header，再调用 `/ir/calc/tasks`。

中台访问令牌：

- 中台配置仅有 `base_url`、`app_id`（本地 `ir-agent`）和 `app_secret`；
- 本地来自 `agent-backend/configs/application.yml`，测试/生产由 Nacos 或部署配置覆盖；
- 后端调用 `/api/v1/auth/token` 获得中台 token；
- 采用进程内缓存，缓存键为 `app_id + userId`，缓存 access token 与过期时间；
- `/chat/diag` 认证失败时，删除该缓存、重新换 token，并只重试同一请求一次；其他业务错误或 SSE 中断不自动重放。

中台 YAML 仍按文档配置固定 `Authorization: Bearer ...` 服务头。本地令牌由 `application.yml` 提供，真实值不提交。第一阶段 IR 后端不校验该固定 Bearer；当前入站校验仍为 `userId` / `username`。

## 中台消息与工具调用

后端发送给中台的用户消息保持用户原文，并仅在其末尾附加：

```text
<ir_system_context>{"conversation_id":42}</ir_system_context>
```

该段不写入用户可见历史，也不暴露给前端。中台从中提取 `conversation_id`，在调用工具时按现有 `/ir/calc/tasks` body 字段传递。除该 ID 外，不在内部上下文增加其他信息。

中台声明包：

```yaml
owner_app_id: ir-agent
backend:
  base_url: http://127.0.0.1:9089

domains:
  - domain_code: energy_storage_calculation
    display_name: 储能项目测算
    tools:
      - name: create_calculation_task
        http:
          method: POST
          path: /ir/calc/tasks
```

最终 YAML 按中台手册的严格字段白名单和实际样例完成。`backend.base_url + tool.http.path` 的本地联调地址是：

```text
POST http://127.0.0.1:9089/ir/calc/tasks
```

中台负责自然语言理解、参数提取、冲突处理、必要追问与工具调用；本应用不重写这些能力。

## 测算参数与 duration_hours

既有测算领域、参数字典、飞书 `API_INPUT` 和快照仍只使用归一化后的：

```text
province, capacity_mwh, power_mw, node_name, voltage_kv,
conversation_id, param_overrides
```

为满足中台暂不具备规模换算的情况，扩展 `POST /ir/calc/tasks` 的接口输入，增加可选 `duration_hours`。它仅存在于接口层：

- 不是参数字典字段；
- 不写飞书 `API_INPUT`；
- 不写最终冻结输入或快照；
- 不改变财务公式。

归一化规则：

| 输入 | 归一化 |
| --- | --- |
| `power_mw + capacity_mwh` | 直接使用 |
| `power_mw + duration_hours` | `capacity_mwh = power_mw * duration_hours` |
| `capacity_mwh + duration_hours` | `power_mw = capacity_mwh / duration_hours` |
| 仅 `duration_hours` | 默认 `power_mw = 100`，再推导容量 |
| 三者都有且一致 | 使用显式 MW/MWh |
| 三者都有且不一致 | HTTP 400 |
| 仅 MW 或仅 MWh | HTTP 400，要求补容量或时长 |

三个值均接受任意正数，不限制固定时长档位。最终业务层继续从 `capacity_mwh / power_mw` 派生内部时长。

运营周期维持现有后端契约：`operation_years` 位于 `param_overrides.operation_years`，仅支持 15 或 20；缺省时由参数字典默认 15。新中台手册已明确 YAML `body` 缩进对应 JSON 嵌套层级，最终工具 YAML 使用嵌套 `param_overrides` 映射。`operation_years` 只选择 15/20 年飞书模板，不写飞书 `API_INPUT`。

## 结果与历史

中台 `answer.data.biz` 保持 IR `/ir/calc/tasks` 的完整响应壳：

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "conversationId": 42,
    "taskId": 123,
    "status": "completed"
  }
}
```

前端按既有响应契约处理：

- `biz.code == 200` 且 `biz.data.status == "completed"`：按现有逻辑刷新/展示测算结果；
- `biz.code == 200` 且 `biz.data.status == "failed"`：展示现有 `data.error`；
- `biz.code != 200`：展示 `biz.msg`。

本阶段不新增完整中台聊天消息持久化，不改变现有任务、快照、结果和报告的数据模型。历史会话的回放继续完全依赖本应用任务、版本、`report_snapshot` 和报告数据。

## 分阶段交付

### 第一阶段

- 数据库增加中台 `session_id` 映射字段与联合唯一索引；
- 新增 `/ir/chat/diag` 后端代理；
- 本地/Nacos 中台三项配置；
- token 缓存、认证失败单次换 token 重试、SSE 原样转发；
- 首条消息创建本应用会话、中台会话映射持久化；
- `duration_hours` 接口层归一化；
- `ir-agent.yaml` 和中台工具注册；
- 验证 `conversation_id -> session_id -> tasks -> 既有结果/报告` 闭环。

### 第二阶段

- 前端首页发送入口切换至 `/ir/chat/diag`；
- 用流式 `fetch` 消费中台 SSE 并读取 `X-IR-Conversation-Id`；
- 复用现有 `conversationId`、结果、历史和报告渲染。

### 第三阶段

- 标题修改接口：`PATCH /ir/conversations/{conversation_id}`，仅当前用户且未删除会话可修改；标题去空白后非空；
- 完整用户消息与中台文本消息持久化及更丰富的会话体验。

## 联调验证项

以下项不阻塞 YAML 与后端代理实现，但需在真实中台联调中验证：

1. 新增 `header` JSON 正确写入工具请求 `userId` / `username` Header；
2. 中台从内部上下文提取 `conversation_id` 并映射到嵌套/普通工具 body 的实际行为；
3. 真实 SSE 帧及 `answer.data.biz` 嵌套形态；
4. 中台工具默认超时与真实飞书同步测算耗时的兼容性；
5. 中台 YAML 的最终严格校验、上传与生效流程。
