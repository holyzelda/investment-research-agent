# 执行合同：PRD-001 · 平台接入与测算主链路

> 本合同为恢复性重建：Batch 0–3 已实质完成，Batch 4 正在执行，Batch 5 尚未开始。DP-3 未批准前，不继续实现。

## Intent Lock

打通“平台跳转承接 → 对话首页 → 飞书副本测算 → 结果三模块 → 快照与多版本”的主链路，验证飞书方案 A（独立 `API_INPUT / API_OUTPUT / API_META` 接口区）。系统供内部低频使用，飞书仍是权威计算器。

### Scope Fence

范围内：
- 无独立登录的 Vue3 前端与 FastAPI 后端；
- 平台 header 身份承接；
- 参数字典、四来源参数组装、飞书接口区读写；
- 测算执行、重试、7 类快照；
- 对话最小输入、结果三模块、版本切换；
- 当前用户历史会话列表、手动回放、软删除与全链路资源归属校验；
- Batch 5 inline 参数调整与重新测算。

范围外：
- 登录、注册、验证码、用户/RBAC、token 二次校验；
- 报告本体/PDF及报告历史（仅预留 `conversation_id/task_id/version` 关联约束）；
- 中台 Tool、通用 NLU/意图分发；
- 地图、政策模块；
- 重写飞书公式。

## Approved Behavior 与覆盖

| 能力 | 批次 | 必须行为 | 主要验证 | 恢复态 |
|---|---:|---|---|---|
| 前端脚手架 | 0 | Vue3/Vite、统一请求壳、XC 设计系统；无登录页和权限守卫；默认落首页 | `scaffold.spec.js`、路由/品牌检查 | 已完成 |
| 后端脚手架 | 0 | `create_app()`、中间件、`{code,msg,data}`、异常处理、异步 SQLAlchemy、Alembic、Nacos 降级 | app boot、响应壳、Nacos fallback、迁移 | 已完成 |
| 平台承接 | 1 | 读取可配置身份 header 注入请求上下文；不校验 token、不访问外部登录态 | 身份存在/缺失、字段切换、无登录代码 | 已完成；生产禁匿名挂账 |
| 参数字典 | 2 | 参数元数据结构化、可版本化；按省份收益结构收敛可见项 | schema、可见集、默认值与类型 | 基础完成；按省端点待 Batch 5 补齐 |
| 飞书接口区 | 2 | 仅复制副本并读写 INPUT/OUTPUT/META，不改模型单元格；5xx 可重试 | gateway 打桩、接口区范围、重试 | 已完成 |
| 参数组装 | 2 | 对话输入、默认值、电价库、表2四来源合并；只读项不写；hash 稳定 | assembler 单元/集成测试 | 已完成 |
| 执行引擎 | 3 | 状态机、request_id/hash 校验、智能重试、失败原因、任务/会话/version 持久化 | engine、retry、API 测试 | 已完成；同步/异步见 X1 |
| 快照 | 3 | 每次落 7 类且不覆盖；`report_snapshot` 可脱离飞书重建结果 | snapshot 与 result API 测试 | 已完成 |
| 首页输入 | 4 | 省份/功率/容量齐全才发起；缺项提示且不请求 | `home.spec.js` | 进行中 |
| 任务编排 | 4 | POST task；非终态轮询；完成后拉 result；失败展示原因和 request_id | `calc-flow.spec.js` | 进行中 |
| 结果三模块 | 4 | 基本信息、5 项财务指标、首年收入环形图、4 条 15 年现金流；电价显示 4 位小数、整数不显示小数点、其他非整数显示 2 位，仅格式化前端展示且不修改快照原值 | `result-cards.spec.js`、`charts.spec.js` | UI 已有，格式化待补 |
| 多版本 | 4 | 使用后端 version；最新标记；点击切换历史快照；报告仅占位提示 | `version-list.spec.js` | 进行中 |
| 历史会话 | 4.6 | 左侧“投资分析工作台”全部功能项之后展示当前用户未删除会话；刷新保持欢迎页并手动打开；固定顺序回放消息、版本和 report_snapshot；继续测算复用 conversation_id | 后端 `test_conversation_history_api.py`、前端 `conversation-history.spec.js` | 未开始 |
| 会话删除与归属 | 4.6 | “…”菜单二次确认；仅写 conversation.deleted_at，保留消息/任务/快照；列表/详情/删除及 task status/result 均按当前 user_id 校验，越权统一 404 | 软删除持久化、快照行数不变、跨用户 404 | 未开始 |
| 参数调整 | 5 | 默认收起；四区；数值滑块/枚举下拉；不重复展示三项派生电价 | `param-adjust.spec.js` | 未开始 |
| 锁项与显隐 | 5 | 首次锁省/节点/功率/容量，二次解锁；按省收益结构显隐，现货始终显示 | 锁项、改省重拉测试 | 未开始 |
| 重新测算 | 5 | 冻结本次入参；同会话创建新任务、新版本，不覆盖旧版本 | V2/V3 追加与历史保留 | 未开始 |

所有 delta spec 的 SHALL/MUST 均归入上述能力；显式延期项包括报告本体、中台意图分发、业务公式最终确认、生产 header/Nacos 配置。

## Design Constraints

- 后端依赖方向：`interface → application → domain`，基础设施实现端口。
- 飞书是唯一权威计算器；应用不复制计算公式。
- `report_snapshot` 是历史结果展示的数据源。
- 前端复用现有 `request.js`、Pinia store、ResultCard 与 ECharts 组件，不增加第二套请求层或通用工作流框架。
- Batch 4 不提前实现 Batch 5；Batch 5 不实现报告本体。
- 遵循简单实现：固定业务规则直接编码，不增加模式开关、自动探测或多重 fallback。

## Execution Batches

### Batch 0–3 · 恢复确认

代码与子任务已实质完成；以现有测试与后续全量回归作为完成证据，不重复实现。

### Batch 4 · 当前执行批

1. 用 `/ir/calc/tasks`、`/status`、`/result` 替换 `/ir/calc/run` 固定参数路径。
2. 实现最小三项解析与缺项提示。
3. store 使用后端 `conversationId/taskId/version`；兼容 POST 直接终态与未来非终态。
4. 完成失败信息、版本切换、报告占位。
5. 补齐五个命名 Vitest 套件并执行全量前端测试/构建。
6. 批末做 spec 合规与代码质量审查。

### Batch 4.6 · 历史会话列表与回放

1. 为 `ir_conversation` 增加可空 `deleted_at` Alembic 迁移，不增加级联删除。
2. 实现当前用户会话列表、详情回放和软删除三个 API；详情一次返回固定顺序消息、版本及 report_snapshot。
3. 为既有 task status/result 查询补 `task → conversation → user_id` 归属校验，越权按 404 处理。
4. 左侧栏按原型采用“投资分析工作台”功能项 → 分隔线 → 历史会话；首页只加载列表，用户手动打开。
5. “…”菜单二次确认软删除；打开历史会话后恢复 store，继续测算沿用 conversation_id。
6. 后端和前端分别完成历史 API/回放/软删除/越权测试，再进行端到端验证和审查。

### Batch 5 · 后续执行批

1. 补 `GET /ir/calc/param-dict?province=` 契约与测试；所有市场（含现货）统一按表2开关显隐。现货沿用已确认的元/kWh 输出口径。
2. 实现 inline 调整区、四区布局和控件范围：日循环1–2/0.1；三类达成率70%–95%/1%；贷款利率3.5%–4.5%/0.1%；EPC 0.70–0.85/0.01；维保/运营0–0.1000/0.0001；动态金额以基准值0–2倍；运营期固定15年、换电成本固定0、贷款年限不展示。
3. 省份永久锁定；首次节点/容量/功率锁定，二次及以后解锁；换省必须新建会话。
4. 扩展任务接口为受控 `param_overrides`，历史详情暴露 input snapshot 作为版本基线。
5. 后端比较上一版本【节点、容量、功率、日循环】：变化则查预计算表覆盖现货价格对；不变则不查库并继承/应用手工价格；`switch_spot=0` 不查库。
6. 用同一 `conversation_id` 重新发起，追加后端版本并保留历史；不修改任何现有现货单位或换算逻辑。
7. 批末执行前后端测试、端到端验证与审查。

## Test Obligations

- 新行为先有失败测试，再写最小实现。
- Batch 4 必须通过：`home.spec.js`、`calc-flow.spec.js`、`result-cards.spec.js`（覆盖电价 4 位、整数无小数点、其他非整数 2 位且不修改原值）、`charts.spec.js`、`version-list.spec.js`、现有前端测试与 `pnpm build`。
- Batch 4.6 必须通过：后端 `test_conversation_history_api.py`（列表过滤、固定顺序回放、软删除保留快照、跨用户 404、task status/result 归属）和前端 `conversation-history.spec.js`（左侧位置、欢迎页、手动回放、复用 conversation_id、更多菜单确认/取消），以及前后端相关回归测试和前端构建。
- Batch 5 必须覆盖：四区/控件范围、省份永久锁、首次锁定/二次解锁、所有市场按表2显隐、受控覆盖、新版本不覆盖，以及现货依赖变化重查/依赖不变继承手工价/开关关闭不查库；开始前 Batch 4.6 必须完成。
- 回归敏感点：响应壳、request_id 串号、7 类快照不覆盖、report_snapshot 独立重建、版本不覆盖、节点缺省不显示。

## Review Gates

- Batch 4：五个命名套件、全量前端测试、构建、实际任务流验证全部通过后进行代码审查。
- Batch 4.6：历史 API、软删除迁移、用户归属测试和前端回放测试全部通过；确认删除不减少消息/任务/快照行数，跨用户资源统一 404，再进行代码审查。
- Batch 5：参数字典按省契约、锁项/显隐/重算测试与端到端验证通过后审查。
- 任一测试失败、需求与实现不一致、合同范围变化时停止执行并回到调查/规划。

## 待批准裁决

- **X1 同步 POST 与轮询**：当前后端 POST 在请求内执行并返回终态；前端将兼容终态直取结果和未来非终态轮询。建议本阶段接受同步实现，不在 Batch 4 引入后台任务系统。
- **X2 节点/电压抽取**：当前最小解析仅覆盖必填三项。建议节点/电压自然语言抽取留给中台；本阶段不扩展前端正则。
- **X3 按省参数字典**：Batch 5 的收益显隐依赖 `param-dict?province=`。建议作为 Batch 5 第一个后端小切片补齐，不阻塞 Batch 4。

## Approval（DP-3）

当前：**待用户显式批准本次 Batch 4.6 合同刷新**。批准内容包括左侧历史布局、欢迎页手动打开、完整回放、更多菜单软删除、资源归属 404、报告历史仅预留关联；批准前不实现 Batch 4.6。
