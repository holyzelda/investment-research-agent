# 政策与市场咨询历史持久化设计

**日期：** 2026-07-24

## 目标与范围

将“政策与市场”模块的用户咨询从前端内存模拟数据改为后端本地业务数据库持久化数据。用户刷新页面后，仍可查看仅属于自己的历史咨询列表和单条完整详情。

本期包含：

- 通过既有政策知识库问答能力生成真实回答。
- 创建、持久化、读取当前用户的咨询记录。
- 历史列表与单条详情接口。
- 前端历史列表、按需加载详情及提交过程状态。
- ORM、手工 DDL 和测试同步。

本期不包含：

- 编辑、删除、批量操作。
- 分页、关键词检索或按省份、主题、状态筛选。
- 跨用户共享、运营后台查看或重新生成历史回答。
- 前端传递用户身份，或后端实现登录、会话、Token 解析、RBAC。

## 身份与访问控制

后端仅从既有平台身份依赖读取固定 `userId` 与 `username` 请求头。前端不得在请求体或查询参数中传递用户 ID。

缺少任一身份 Header 时返回 401。所有列表和详情查询都按当前 `userId` 过滤；记录不存在或不属于当前用户时统一返回 404，不泄漏记录归属。

## 数据模型

新增 `consultation_records` 表，字段如下：

| 字段 | 说明 |
| --- | --- |
| `id` | 主键；采用项目 ORM 的跨 SQLite/目标数据库兼容主键声明。 |
| `user_id` | 平台用户 ID，非空。 |
| `question` | 用户原始问题，非空。 |
| `answer` | 问答结果；处理中或失败时可为空。 |
| `province_code` | 问答返回的省份信息；可为空，仅作元数据保留。 |
| `topic` | 预留元数据；本期不用于查询。 |
| `status` | `processing`、`completed`、`failed`。 |
| `source_data` | JSON 快照，保存来源、时效信息与提醒。 |
| `created_at` | 创建时间。 |
| `answered_at` | 成功得到回答的时间；可为空。 |
| `updated_at` | 最近更新时间；由 ORM 更新策略维护。 |

建立索引 `idx_consultation_user_time (user_id, created_at DESC)`，以支持当前用户历史记录倒序加载。本期不建立按省份索引，因为没有对应查询场景。

新增 ORM 时必须同步更新 `agent-backend/sql/` 下手工建表 DDL；JSON、主键及时间字段应遵循现有跨环境 ORM/DDL 模式。

## 后端架构与问答执行

在 `policy_market` 模块内遵守 `interface → application → infrastructure` 边界：

- interface：声明请求/响应模型和路由，只负责 HTTP 参数、身份依赖与统一 `{code, msg, data}` 响应壳。
- application：编排创建记录、调用问答执行器、更新状态和读取记录。
- infrastructure：实现 SQLAlchemy 仓储和问答执行器。

真实问答来源为 `agent-backend/tools/policy_ask.py`。`main()` 是命令行交互入口；服务端应直接调用可复用的 `ask(question)` 函数，禁止通过 subprocess 模拟调用 `main()`。

`ask(question)` 为同步且可能耗时的外部 I/O 操作。应用服务应在线程执行器中调用它，避免阻塞 FastAPI 异步事件循环。为保证单元测试隔离外部飞书与 LLM，问答执行器应以可替换端口封装；测试使用替身返回固定结果。

问答结果结构固定为：

```json
{
  "answer": "回答正文",
  "sources": ["来源 URL"],
  "timeliness": {
    "province": "省份或跨省标识",
    "as_of": "信息时点",
    "status": "资料状态"
  },
  "reminders": ["风险提示"]
}
```

成功时：

- `answer` 写入结果正文；
- `province_code` 写入 `timeliness.province`；
- `source_data` 固化为 `{ "sources": [], "timeliness": {}, "reminders": [] }` 结构；
- 状态更新为 `completed`，写入 `answered_at`。

问答调用发生异常时，记录更新为 `failed`，保留问题和创建时间，不伪造答案。接口返回统一业务错误，前端把临时项标为失败。

`policy_ask.py` 内当前存在敏感配置的明文定义。本次实现不得复制或写入这些值至源码、DDL、测试或文档；应将其迁移至受管控环境变量或配置中心，并从脚本中移除明文配置。

## API 契约

所有 API 均以 `/ir/policy-market` 为前缀，并使用统一响应壳。

### 创建咨询

`POST /consultations`

请求体：

```json
{ "question": "用户输入的问题" }
```

后端创建 `processing` 记录，调用问答能力；成功后返回完整详情。问题为空或格式不合法时返回 HTTP 400。

### 历史列表

`GET /consultations`

仅返回当前用户记录，按 `created_at` 倒序。列表使用轻量字段：

```json
{
  "id": 101,
  "title": "新能源消纳政策有何变化？",
  "question": "新能源消纳政策有何变化？",
  "status": "completed",
  "createdAt": "2026-07-24T10:42:00",
  "answeredAt": "2026-07-24T10:42:03"
}
```

### 单条详情

`GET /consultations/{record_id}`

仅返回当前用户拥有的完整记录：

```json
{
  "id": 101,
  "title": "新能源消纳政策有何变化？",
  "question": "新能源消纳政策有何变化？",
  "answer": "回答正文",
  "provinceCode": null,
  "topic": null,
  "status": "completed",
  "sourceData": {
    "sources": ["来源 URL"],
    "timeliness": {},
    "reminders": []
  },
  "createdAt": "2026-07-24T10:42:00",
  "answeredAt": "2026-07-24T10:42:03"
}
```

## 前端数据流

移除 `src/api/policyMarket.js` 中的咨询数组与延时 mock，新增真实请求封装：

- `getConsultations()`：获取历史摘要列表。
- `getConsultation(id)`：获取单条完整详情。
- `submitConsultation({ question })`：提交咨询并获取完整结果。

`policyMarket` Pinia Store 继续作为页面唯一业务状态入口：

1. `loadConsultations()` 加载列表并默认选中第一项。
2. 选择历史记录时先切换选中状态，再按需加载详情，避免列表请求传输全部回答和来源快照。
3. 提交时先插入仅用于 UI 的 `processing` 临时记录；成功后用后端完整记录替换，并同步列表；失败后将临时项标为 `failed` 并显示错误。
4. 详情和提交失败均不得清空此前成功的数据，也不得伪造成功回答。

列表消费轻量字段；结果组件消费详情中的 `answer`、`sourceData` 和 `answeredAt`。前端仅按照已定义的 `sourceData` 字段展示来源快照，不再将临时 `sourceScope` 作为持久化契约。

## 错误处理

- 缺失身份：401。
- 非法请求：HTTP 400 与统一业务响应。
- 本人不存在的记录、非本人记录：404。
- 问答执行失败：记录持久化为 `failed`，调用方得到明确业务失败提示。
- 前端对列表、详情和提交分别维护 loading/error 状态，保留已成功加载内容。

## 测试与验收

后端测试至少覆盖：

1. 当前用户只能获得自己的历史列表，且结果倒序。
2. 本人可读取单条详情。
3. 不存在记录与非本人记录均为 404。
4. 缺失身份 Header 为 401。
5. 创建成功后，问题、答案、状态、来源快照及时间字段正确持久化。
6. 问答执行异常时，记录更新为 `failed`，不写入伪造答案。
7. 替身问答执行器可覆盖成功、异常场景，测试不访问飞书或 LLM。

前端测试至少覆盖：

1. 初始化调用历史列表 API 并展示结果。
2. 选择历史项时调用详情 API 并展示完整回答。
3. 提交后先显示处理中，再以成功结果替换临时项。
4. 提交和详情失败时展示失败状态或提示，且不伪造成功回答。

验收标准：刷新页面后，当前用户仍能看到自己的咨询历史；其他用户不能读取其列表或详情；真实问答结果与来源快照被一次性冻结到本地数据库；前后端均保持既有身份协议与响应壳。