# 前端接入中台流式对话 + 思考过程渲染 — 设计文档

> 日期：2026-07-28
> 范围：前端首页测算主入口改为经我方后端封装接口 `POST /ir/chat/diag` 的流式对话链路；复刻 `etrader-agent-nx` 的“思考过程”展示；重新测算保留直调但统一为同款进度体验。
> 状态：待用户确认。

## 1. 背景与目标

当前首页把用户输入当作“测算任务”的薄包装：前端用正则从自由文本提取省份/功率/容量，缺项本地拦截，然后 `POST /ir/calc/tasks` + 每秒轮询 + 拉结果，界面只显示静态“测算中…”，没有思考过程。

本次目标：

1. **前端主测算入口改为调用我方后端封装接口** `POST /ir/chat/diag`（流式），前端不直连中台。
2. **移除前端本地参数解析/校验/拦截**——补全与追问全部交给中台内部编排。
3. **复刻 nx 的“思考过程”流式展示**（节点链、逐字、取消、终态），页面渲染仍用我们自己的布局与 XC 设计体系。
4. **测算结果卡片**从流式 `answer` 事件拿到 `taskId` 后，另调一次 `GET /ir/calc/tasks/{taskId}/result` 渲染现有 `ResultCard`。
5. **重新测算保留直调** `/ir/calc/tasks`，但展示改成与思考过程一致的统一进度体验。

## 1.5 中台请求契约（锁定）

前端只调我方 `POST /ir/chat/diag`，body 为 `{ message, conversation_id? }`。后端据此组装并调用中台 `/api/v1/chat/diag`，body 锁定为：

```json
{
  "session_id": null,
  "injected_domain": null,
  "entry_type": "open_chat",
  "pinned_domain": null,
  "page_context": null,
  "source_system": "ir_agent",
  "end_user_id": "<user.user_id>",
  "end_user_name": "<user.username 明文 UTF-8>",
  "app_id": "ir_agent",
  "message": "<用户原文，不注入 ir_system_context>",
  "locale": "zh-CN",
  "header": {
    "username": "<quote(user.username)>",
    "userid": "<user.user_id>",
    "conversation_id": "<我方 conversation UUID>"
  }
}
```

要点：
- **两套 id**：`session_id` 是中台会话 id（首轮 null，中台在流里回传后写回映射列，多轮带上）；`header.conversation_id` 是我方会话 UUID（中台回调 `/ir/calc/tasks` 时作为 HTTP header 注入）。
- **顶层 `end_user_*`** 是中台自身身份字段（snake_case 固定），明文填充。
- **`header.*`** 是中台回调我方 `/tasks` 时注入的 HTTP header；键名大小写不敏感（Starlette/FastAPI 大小写无关），`username` URL 编码（回调时中间件 `unquote`），`conversation_id` 供 `/tasks` 的 `Header(alias="conversation_id")` 读取。
- **不再注入 `<ir_system_context>`**，`conversation_id` 改走 `header`。
- `app_id`/`source_system` 统一 `ir_agent`（下划线）。

## 2. 架构边界（不可突破）

- 前端永远只调用我方接口。中台地址、Token、`app_id`、`app_secret` 只在后端。
- 会话 UUID 由后端创建并持有，是 `session_id`、`<ir_system_context>`、测算 `conversation_id`、快照归属的同一把键。
- 参数补全/意图理解在中台内部编排；测算业务规则（2h 推导、飞书测算、快照、版本）在我方 `/ir/calc/tasks`。
- 颜色走 `var(--xc-*)`，不硬编码 hex/rgb；图表复用 `useEcharts`。
- 本次前端为主，后端 `/ir/chat/diag` 维持透传；后端健壮性与落库列为待办，不强绑本 PR。

## 3. 真实事件契约（依据实调 SSE）

事件序列：`session_start` → 多个 `thinking` → `answer` → `recommended_questions` → `done`（异常时 `error`）。

| 事件 | 关键字段 | 前端处理 |
|---|---|---|
| `session_start` | `data.session.session_id` | 记录会话 UUID（亦可用响应头 `X-IR-Conversation-Id`） |
| `thinking`（边界帧） | `node_id`、`node_seq`、`node_title`、`node_status`、`substeps`（`text` 为空） | upsert 节点、更新生命周期/子步骤 |
| `thinking`（token 帧） | `text` + `node_id`/`ref_node_id`（无 `node_status`） | 逐字追加到对应节点私有思考文本 |
| `answer` | `data.type='energy_storage.calculation_task'`；`data.biz[].tool='create_calculation_task'`；`data.biz[].payload`=我方响应壳 `{code,msg,data:{conversationId,taskId,version,status,input}}` | 命中测算工具 → 取 `taskId` → 拉 result → 生成结果卡片 |
| `recommended_questions` | `data.recommended_questions: string[]` | 落数据（展示位后续，见 §7） |
| `done` | `data.reason` | 终态收尾、解锁输入 |
| `error` | `{code,msg,data}` | 错误气泡 |

SSE `id:` 单调递增，用于思考节点 reducer 的去重/防乱序。

> 注意：`answer.biz[].payload.data` 只含 `input`（冻结入参），**不含** `result` 三模块，因此三模块数值必须另调 `GET /ir/calc/tasks/{taskId}/result`（用户已确认方案 1）。

## 4. 前端改动清单

### 4.1 新增 `src/utils/chatSse.js`（POST-SSE 客户端）

在 `reportSse.js` 基础上扩展为对话主传输：

- `fetch` + POST body（`{ message, conversation_id? }`），非 `EventSource`（需带鉴权头 + POST）。
- 复用 `getToken()`/`getUserIdentity()` 注入 `Authorization`/`userId`/`username`（URL 编码）。
- 暴露 `AbortController`（供取消）。
- SSE 解析：跨 chunk 半帧缓冲、`\n\n`/`\r\n\r\n` 分帧、多行 `data:` join、CRLF、`event:`/`id:`/`data:` 三字段。
- 响应非 2xx：读取 body 抛 `HTTP <status>` 错误；**401 前置处理**，与 `request.js` 的 `handleUnauthorized` 语义一致（fetch 不经 axios 拦截器，需手动接同一登录失效逻辑）。
- 返回 `{ close() }`（abort 本地请求）；本地 abort 归一化为“正常结束”，不当错误。
- 事件回调 `onEvent({ type, id, data })`，`type` 取 `event:` 优先、否则 `data.event`、否则 `'message'`。

### 4.2 新增 `src/utils/thinkingChain.js`（节点链 reducer，移植自 nx）

框架无关的纯函数 reducer，便于单测：

- 状态 `{ nodesById, order, lastFrameId }`。
- frameId 幂等/顺序守卫：`frameId <= lastFrameId` 丢弃。
- 稳定节点身份：按 `node_id` upsert，非 append-only。
- 执行顺序独立于到达顺序：按 `node_seq` 插入 `order`。
- 仅最新 active 节点默认展开，其余折叠。
- 完成只由显式 `node_status`（`completed`/`aborted`）决定，text 结束不算完成。
- `substeps` 作为服务端快照整体替换（支持“完成 M/N”刷新）。
- 流关闭时安全收尾：残余 active → completed 并折叠；`waiting_user` 为合法终态。

### 4.3 新增思考过程组件

- `src/views/home/components/ThinkingChain.vue`：深色容器、品牌标题、运行态动画、完成后链级折叠、节点分隔、bootstrap/bridge 占位态。
- `src/views/home/components/ThinkingNodeItem.vue`：节点标题、重复序号徽标、active/waiting/aborted/done 状态图标、子步骤进度、可展开的思考文本。
- 颜色全部走 `--xc-*`；视觉基线保持我们自己的风格（不照搬 nx 皮肤，只复刻结构与交互逻辑）。

### 4.4 `store/modules/calculation.js`

- **删除** `extractMinInput`（及其 `PROVINCES`）与 `sendAndCalculate` 中的正则/缺项/阻止提交逻辑。
- `sendAndCalculate(text)` 改为：
  1. 推用户消息；
  2. 建一条 `kind: 'assistant-stream'` 助手消息（含 `thinkingState`、流式 `answerText`、`result` 占位、`recommendedQuestions`、终态标记）；
  3. 打开 `chatSse` 流，按事件原地更新该消息；
  4. `answer` 命中测算工具 → `getCalculationResult(taskId)` → 该消息补 `result/version/input/calculatedAt`，同时 push `versions` 并更新 `selectedVersion`；
  5. `done`/`error`/本地取消 → 收尾、解锁。
- 用 `activeStream`（含 `abortController`）跟踪在途流；`responding` 继续保留供现有 UI 消费点（Composer/chips/ResultCard/ParamAdjustPanel），避免破坏其他调用点。
- 会话延续：流首个 `session_start`（或响应头）确定 `conversationId`；后续请求带上它。

### 4.5 重新测算 `recalculate` — 直调但统一体验

- 仍直调 `POST /ir/calc/tasks` + `_waitForTerminal` + `getCalculationResult`（业务规则、参数结构不变）。
- 展示改为同款进度态：推入一条 `kind: 'assistant-stream'` 消息，但其 `thinkingState` 用一个**同风格的“测算进行中”占位节点**（等价 nx 的 bootstrap/bridge），完成后同样升级为 ResultCard。
- 结果：首测（真实中台 thinking 流）与重测（本地进度占位）复用同一套展示组件与消息形态，体验统一。

### 4.6 `src/api/calc.js`

- 保留 `getCalculationResult`（结果三模块取数）。
- 保留 `getCalculationTask`/`_waitForTerminal` 供重新测算与可能的兜底；对话主链路不再轮询。
- 新增对话流不放这里（`chatSse.js` 自持鉴权，不走 axios 实例）。

### 4.7 `views/home/index.vue`

- 消息渲染新增 `kind: 'assistant-stream'` 分支：`ThinkingChain` + 流式文本气泡 + 内嵌 `ResultCard`（result 就绪后）。
- 保留现有 `text`/`result`/`report-progress`/`report-generated` 分支（历史恢复仍会产出 `result` 分支）。
- 复用现有 `ResultCard`、版本记录栏、报告链路，不改其数据契约。
- 流式期间自动滚动跟随（参考 nx 的 anchor 逻辑，或沿用现有 `scrollTop` 简版，见 §7）。

## 5. 保持不变

- `ResultCard` 三模块、参数调整面板、版本记录栏、报告链路、历史会话 CRUD、XC 设计体系与颜色 token。
- `recalculate` 的业务参数与后端契约。

## 6. 后端改动（与前端分开，动前先读 agent-backend/CLAUDE.md）

### 6.1 中台请求 body 修正（`chat_proxy_service.py`）

当前偏差：
- 把我方 `conversation.id` 作为中台 `session_id` 发出（line 88）；
- `header` 只有 `userId`/`username`，缺 `conversation_id`（line 95-98）；
- 注入了 `<ir_system_context>`（line 80-84，但未实际拼进 message，变量 `context` 未使用）；
- 缺顶层字段 `injected_domain`/`source_system`。

修正为 §1.5 锁定契约：
- `session_id`：用映射列存的中台会话 id（首轮 null，§6.2 从流抓回并存）；
- `header` 补 `conversation_id`（我方 UUID）；
- 删除 `context` 变量及拼接；
- 补 `injected_domain: null`、`source_system: “ir_agent”`。

### 6.2 中台 session_id 映射列（新增 migration）

- **新增字段**：`Conversation.middle_platform_session_id: str | None`（可空，首轮未回传前为 null）。
- **存储时机**：`_validate_session_start` 从 `session_start` 事件抓取中台 session_id 后，写回 `conversation.middle_platform_session_id` 并 commit。
- **回填时机**：`start_chat` 在 `conversation` 已存在时（多轮），读取 `conversation.middle_platform_session_id` 填入中台 body 的 `session_id`。

当前 `_validate_session_start` 校验”中台 session_id 必须等于我方 conversation.id”（line 161），此前提已不成立（两套 id 独立）。改为：
1. 抓取中台 `session_id`；
2. 写回 `conversation.middle_platform_session_id`（异步 commit）；
3. 不校验相等，只校验非空且合法字符串。

### 6.3 app_id 统一为 `ir_agent`

改动范围：
- `configs/application.yml`: `middle_platform.app_id` → `ir_agent`；
- `ir-agent.yaml`: 文件内 `app_id` 字段（若有）→ `ir_agent`；文件名可选改为 `ir_agent.yaml`（如不影响加载路径）；
- `chat_proxy_service.py:86`: payload 中 `app_id` 已用 `self._config.app_id`，配置改后自动同步。

### 6.4 `/tasks` 保持不变

`router.py` 的 `create_task` 已从 `Header(alias=”conversation_id”)` 读我方会话 UUID，逻辑正确，不改。

### 6.5 后端健壮性待办（列出，不强绑本次）

1. **聊天记录未落库**：`/ir/chat/diag` 未持久化用户消息/助手文本/思考节点/终态。
2. **历史恢复显式关联**：需提供 `messageId ↔ taskId/version` 显式映射，替代位置配对。
3. **SSE 健壮性**：`session_start` 作为必需首帧强制校验、错误/超时/断线归一化为稳定 error 帧、401 刷新重试、连接/空闲超时。
4. **配置安全**：`application.yml` 含明文中台/飞书密钥，应改为忽略的密钥覆盖或环境/Nacos 下发。

## 7. 待细化项（实现中按最小可用推进）

- `recommended_questions` 展示位：现有 UI 无“推荐问题胶囊”位置，先落数据，展示为可选增量（可在流末或输入框上方补胶囊）。
- 流式自动滚动：优先沿用现有 `index.vue` 的 `scrollTop` 简版；若跟随不稳再引入 nx 的 anchor + RAF。
- 取消交互：Composer 在 `responding` 时是否改为“停止”按钮（nx 有）——本次可先保留禁用态，取消能力由 `activeStream.close()` 预留。

## 8. 验证

- 单测：`thinkingChain.js` reducer（去重、乱序、节点身份、substeps 快照、终态收尾）。
- 单测/组件测：`sendAndCalculate` 事件序列（session_start→thinking→answer→done）、answer 命中测算工具后拉 result 并升级为版本、error 终态、取消。
- 保留并更新现有 `tests/calc-flow.spec.js`（原轮询契约将被流式契约取代，需改写）。
- 跑 `npm test`、`npm run build`。
