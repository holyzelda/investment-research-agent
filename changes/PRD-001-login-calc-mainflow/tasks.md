# 实现任务：PRD-001 · 平台接入与测算主链路

> 约定：前端测试用 `vitest`，后端测试用 `pytest`（在 `agent-backend/.venv` 中，Windows 路径 `agent-backend/.venv/Scripts/python.exe -m pytest`）。每个任务遵循 TDD 五步。Batch 依赖显式标注，只依赖更前批次。

## 文件结构

### 前端 `agent-frontend/`（全新工程 · XC 设计体系 + 通用框架层 · 无登录页）
- `Create: agent-frontend/**` — 全新 Vite+Vue3 工程；通用框架层（axios 请求实例、`layout/`、路由、通用组件、svg-icon、nprogress）
- `Create: agent-frontend/src/design-system/**` — 移植 XC 玄策（tokens.css / element-plus-overrides.scss / CHARTS.md / design-system.md）
- `Create: agent-frontend/.env.development|.env.production|.env.staging` — 仅网关基地址/标题/favicon/env
- `Create: agent-frontend/src/settings.js`、`index.html`、`public/` 品牌资源 — 朱雀品牌化
- `Create: agent-frontend/src/views/home/index.vue` — 对话首页工作台（默认落地页，承接平台跳转）
- `Create: agent-frontend/src/views/home/components/ResultCards.vue` — 结果三模块 inline 卡片
- `Create: agent-frontend/src/views/home/components/RingChart.vue`、`CashflowLineChart.vue` — 环形图/折线图（ECharts）
- `Create: agent-frontend/src/views/home/components/ParamAdjustPanel.vue` — inline 参数调整区
- `Create: agent-frontend/src/views/home/components/VersionList.vue` — 右侧版本记录
- `Modify: agent-frontend/src/layout/components/AppSidebar.vue` — “投资分析工作台”功能导航及功能项之后的历史会话列表/更多菜单
- `Modify: agent-frontend/src/store/modules/calculation.js` — 历史列表加载、会话回放、软删除后的状态同步
- `Modify: agent-frontend/src/api/calc.js` — 测算任务与会话列表/详情/软删除接口
- `Create: agent-frontend/tests/conversation-history.spec.js` — 历史会话布局、手动回放、软删除前端验收

### 后端 `agent-backend/`（团队统一栈 · 自研，不抄 trader 代码）
- `Create: agent-backend/app/main.py` — FastAPI 应用工厂（CORS→日志→平台身份中间件、生命周期、register_routers）
- `Create: agent-backend/app/router.py` — 路由集中注册
- `Create: agent-backend/app/core/config/settings.py`、`db_settings.py`、`database.py` — 配置（yaml + Nacos）
- `Create: agent-backend/app/clients/nacos_client.py` — Nacos 客户端
- `Create: agent-backend/app/clients/feishu_client.py` — 飞书接口区读写客户端（httpx + tenacity）
- `Create: agent-backend/app/core/middleware/platform_identity_middleware.py`、`common/constants.py` — 从请求头读取 user_id/username 注入 request.state（字段名可配）
- `Create: agent-backend/app/core/exception_handlers.py`、`app/utils/response.py` — 响应壳与异常
- `Create: agent-backend/app/core/deps.py` — DB 会话/当前用户（来自 header）依赖
- `Create: agent-backend/app/db/models/ir_agent/*.py` — 7 类快照 + 会话/消息/任务 ORM
- `Create: agent-backend/app/db/dao/ir_agent/*_dao.py` — DAO
- `Create: agent-backend/app/modules/calc/service/{param_dict,param_assembler,feishu_calc_engine,retry_policy,snapshot_service}.py` — 测算领域服务
- `Create: agent-backend/app/modules/calc/router.py`、`schemas.py` — 测算接口与 DTO
- `Create: agent-backend/app/modules/calc/data/param_dict.json` — 参数字典结构化文件（待业务校对）
- `Create: agent-backend/configs/application.yml`、`.env.test`、`.env.prod` — 本地配置
- `Create: agent-backend/alembic.ini`、`agent-backend/migrations/**` — Alembic
- `Create: agent-backend/tests/**` — pytest
- `Modify: agent-backend/app/modules/calculation/infrastructure/persistence/orm.py` — `ir_conversation.deleted_at` 软删除字段
- `Create: agent-backend/migrations/versions/*_add_conversation_deleted_at.py` — 历史会话软删除迁移
- `Create: agent-backend/app/modules/calculation/application/conversation_history_service.py` — 当前用户会话列表/详情回放/软删除及归属校验
- `Modify: agent-backend/app/modules/calculation/interface/router.py` — 会话历史接口与 task status/result 用户归属校验
- `Create: agent-backend/tests/db/test_conversation_history_api.py` — 历史列表、回放、软删除、越权 404 测试

## 接口

### Batch 1 → 所有业务批次
- **Produces**: `PlatformIdentityMiddleware` / `get_current_user` 依赖 — 从请求头读取 `user_id/username` 注入 `request.state`（字段名可配），供快照 `conversation` 归属；不做校验、无 401 令牌逻辑

### Batch 2 → Batch 3、Batch 4
- **Produces**: `FeishuClient.copy_template() -> copy_url`、`write_input(copy, cells)`、`read_output(copy) -> dict`、`read_meta(copy) -> {status, request_id}`
- **Produces**: `ParamAssembler.assemble(min_input) -> InputSnapshot`（默认值+表2+电价库引用+对话抽取）
- **Produces**: `GET /ir/calc/param-dict?province= -> {params[], visibility}` — 参数元数据（显示F/可调G/显隐/默认/单位/类型）

### Batch 3 → Batch 4
- **Produces**: `POST /ir/calc/tasks {min_input|frozen_input} -> {task_id, version}`
- **Produces**: `GET /ir/calc/tasks/{task_id} -> {status, version, request_id, error?}`
- **Produces**: `GET /ir/calc/tasks/{task_id}/result -> report_snapshot`（基本信息/财务指标/首年各收益/15年序列）

### Batch 4 → Batch 5
- **Produces**: 首页对话视图 + `ResultCards` + `VersionList`（消费 Batch 3 接口）
- **Produces**: `GET /ir/conversations -> {items:[{conversationId,title,createdAt,latestVersion,latestStatus}]}`（仅当前用户且 `deleted_at IS NULL`）
- **Produces**: `GET /ir/conversations/{conversationId} -> {conversationId,title,messages[],versions[]}`（消息固定顺序，versions 含 taskId/version/status/result）
- **Produces**: `DELETE /ir/conversations/{conversationId} -> {conversationId,deleted:true}`（当前用户软删除）
- **Produces**: 历史会话打开后的 `conversationId` — 被 Batch 5 重新测算追加版本消费

---

## 0. Batch 0：仓库与双应用脚手架

依赖：无。

- [x] **0.1 前端全新工程 + 框架层 + 设计体系（无登录页）**
  - **0.1.1** 编写启动自检测试：`agent-frontend/tests/scaffold.spec.js` 断言 `import.meta.env.VITE_APP_BASE_API` 存在、axios `request` 拦截器按 `{code,msg,data}` 解析、路由默认落地对话首页、源码中**无** login/register/captcha/permission-guard、无 `ecenter`/`systemSign`。
  - **0.1.2** 运行 `npm exec vitest -- run tests/scaffold.spec.js`，Expected: FAIL（工程未建）。
  - **0.1.3** `npm create vite@latest agent-frontend -- --template vue`；对齐 trader 依赖版本（vue/element-plus/pinia/vue-router/echarts/tailwindcss/vue-slider-component/nprogress）；搭建通用框架层（axios 请求实例、`layout/`、路由、通用组件、svg-icon）——**不含登录页/路由守卫/用户权限模块**；移植 `src/design-system/`（XC）；配 `.env.*`（`VITE_APP_BASE_API=/gateway/`、`VITE_APP_TITLE=朱雀投研智能体`、favicon）；根路由默认指向 `views/home`。
  - **0.1.4** 运行 `npm ci && npm exec vitest -- run tests/scaffold.spec.js`，Expected: PASS；`npm run dev` 启动直达对话首页、无未捕获错误。
  - **0.1.5** 提交 `feat(frontend): bootstrap fresh Vue3 app (XC design system + framework layer, no login)`。
  - **Files**: `Create: agent-frontend/**`

- [x] **0.2 后端 FastAPI 基座（团队统一栈）**
  - **0.2.1** 编写 `agent-backend/tests/test_app_boot.py`：用 `TestClient(app)` 断言 `GET /health` 返回 200 且 body `{"code":200,...}`；`GET /docs` 200。
  - **0.2.2** 运行 `agent-backend/.venv/Scripts/python.exe -m pytest tests/test_app_boot.py -q`，Expected: FAIL（无 app）。
  - **0.2.3** 自研创建 `app/main.py`（`create_app()`、中间件顺序、生命周期）、`app/router.py`、`core/config/settings.py`、`core/exception_handlers.py`、`app/utils/response.py`、`core/config/database.py`（异步引擎/会话，主源 `ir_agent`）、`core/deps.py`、`common/constants.py`、`configs/application.yml`、`.env.test`。建 `.venv` 并 `pip install fastapi uvicorn sqlalchemy[asyncio] asyncmy alembic httpx tenacity apscheduler pydantic-settings pyyaml loguru "nacos-sdk-python" pytest`（无需 redis/passlib/jwt——不做登录）。
  - **0.2.4** 运行同上，Expected: PASS。
  - **0.2.5** 提交 `feat(backend): FastAPI app factory + response envelope + async session (team stack)`。
  - **Files**: `Create: agent-backend/app/main.py, app/router.py, app/core/**, app/utils/response.py, configs/**`
  - **Interfaces**: Produces `{code,msg,data}` 响应壳、`get_db_session` 依赖 — 被后续所有批次消费。

- [ ] **0.3 Nacos 装载 + ir_agent 建库 + Alembic**
  - **0.3.1** 编写 `tests/test_nacos_fallback.py`：`NACOS_ENABLED=false` 时 `init_database_config_from_env()` 用本地 `.env` 且不抛错。
  - **0.3.2** 运行 pytest，Expected: FAIL。
  - **0.3.3** 创建 `app/clients/nacos_client.py` 与 `settings.py` 的 Nacos 装载/降级；`alembic init migrations`，配置 `alembic.ini` 指向 `ir_agent`；建库 SQL/说明。
  - **0.3.4** 运行 pytest，Expected: PASS；`alembic upgrade head` 在空库成功。
  - **0.3.5** 提交 `feat(backend): nacos config load with local fallback + alembic init`。
  - **Files**: `Create: app/clients/nacos_client.py, alembic.ini, migrations/**`

## 1. Batch 1：平台接入与承接

依赖：Batch 0。

- [x] **1.1 后端平台身份读取中间件**
  - **1.1.1** 编写 `tests/test_platform_identity.py`：请求头含约定字段（如 `X-User-Id`/`X-User-Name`，字段名从配置读取）→ 中间件解析并注入 `request.state.user_id/username`；缺失时按可配策略（开发→匿名占位放行；生产→按约定处理）；**断言不存在任何 401 令牌校验、不访问 Redis/外部登录态**。
  - **1.1.2** 运行 `agent-backend/.venv/Scripts/python.exe -m pytest tests/test_platform_identity.py -q`，Expected: FAIL。
  - **1.1.3** 实现 `core/middleware/platform_identity_middleware.py`（从 header 读取、字段名来自 Nacos/env、注入 request.state）、`core/deps.py` 的 `get_current_user`（从 request.state 取）、`common/constants.py`；注册中间件到 `create_app()`（在请求日志之后）。
  - **1.1.4** 运行 pytest，Expected: PASS。
  - **1.1.5** 提交 `feat(platform): trust-header identity middleware (no login)`。
  - **Interfaces**: Produces `PlatformIdentityMiddleware` / `get_current_user` — 被 Batch 3/4 快照归属消费。

- [ ] **1.2 前端承接落地对话首页**
  - **1.2.1** 编写 `tests/landing.spec.js`：根路由 `/` 渲染 `views/home`（对话首页）；无登录页/无守卫重定向；标题=`VITE_APP_TITLE`、根节点带 `xc-app` class。
  - **1.2.2** 运行 `npm exec vitest -- run tests/landing.spec.js`，Expected: FAIL。
  - **1.2.3** 配置路由默认落地 `views/home`；`layout` 承载对话首页；确认请求实例透传（同域时浏览器自带平台注入的 header，无需前端处理身份）。
  - **1.2.4** 运行 pytest，Expected: PASS。
  - **1.2.5** 提交 `feat(frontend): land on conversation home (platform handoff, no login)`。

## 2. Batch 2：参数字典、飞书客户端、参数组装

依赖：Batch 0。

- [ ] **2.1 参数字典结构化文件与下发接口**
  - **2.1.1** 编写 `tests/test_param_dict.py`：加载 `param_dict.json` 校验 schema（每项含 name/cell/source/default/unit/type/showF/adjustG/interfaceCell）；`GET /ir/calc/param-dict?province=甘肃` 返回按表2 收敛的可见集合。
  - **2.1.2** 运行 pytest，Expected: FAIL。
  - **2.1.3** 创建 `modules/calc/data/param_dict.json`（依 F=1+表2 结构，值标注"待业务校对"）、`service/param_dict.py`、`modules/calc/router.py` 下发接口、`schemas.py`。
  - **2.1.4** 运行 pytest，Expected: PASS。
  - **2.1.5** 提交 `feat(calc): parameter dictionary file + metadata endpoint`。
  - **Interfaces**: Produces `GET /ir/calc/param-dict` — 被 Batch 4/5 消费。

- [x] **2.2 飞书接口区客户端**
  - **2.2.1** 编写 `tests/test_feishu_client.py`：用 `respx`/httpx mock 断言 `copy_template()` 返回副本标识、`write_input(cells)` 写入 `API_INPUT`、`read_meta()` 解析 `{status,request_id}`、`read_output()` 解析结果；5xx 经 tenacity 重试。
  - **2.2.2** 运行 pytest，Expected: FAIL。
  - **2.2.3** 实现 `clients/feishu_client.py`（httpx + tenacity，凭证/表 token 来自 Nacos），仅读写 `API_INPUT/API_OUTPUT/API_META`。
  - **2.2.4** 运行 pytest，Expected: PASS。
  - **2.2.5** 提交 `feat(calc): feishu interface-zone client (scheme A)`。
  - **Interfaces**: Produces `FeishuClient` — 被 Batch 3 消费。

- [x] **2.3 参数四来源组装服务**
  - **2.3.1** 编写 `tests/test_param_assembler.py`：给定最小输入（甘肃/800MWh/200MW）→ 断言默认值填充、表2 条件取数（只取参与项）、只读项不写入、电价库均价字段以 stub 注入、参数 hash 稳定。
  - **2.3.2** 运行 pytest，Expected: FAIL。
  - **2.3.3** 实现 `service/param_assembler.py`（默认值/表2 取数/电价库引用接口 stub/对话抽取入参合并 → `InputSnapshot`），`service/province_table2.py` 表2 取数。
  - **2.3.4** 运行 pytest，Expected: PASS。
  - **2.3.5** 提交 `feat(calc): four-source parameter assembler`。
  - **Interfaces**: Produces `ParamAssembler.assemble` — 被 Batch 3 消费。

## 3. Batch 3：测算执行引擎与快照

依赖：Batch 2。

- [ ] **3.1 ir_agent 快照/会话/任务 ORM + 迁移**
  - **3.1.1** 编写 `tests/test_snapshot_models.py`：SQLite/内存库建表并 CRUD 断言 7 类表 + conversation/message/calculation_task 字段（含 JSON 列、version、feishu_copy_url、request_id、status；`conversation` 含 `user_id`/`username` 归属字段，来源为平台注入 header）。
  - **3.1.2** 运行 pytest，Expected: FAIL。
  - **3.1.3** 实现 `db/models/ir_agent/*.py`（Base、conversation、message_snapshot、calculation_task、input_snapshot、data_snapshot、feishu_io_snapshot、report_snapshot）、`db/dao/ir_agent/*_dao.py`；生成 `alembic revision --autogenerate`。
  - **3.1.4** 运行 pytest + `alembic upgrade head`，Expected: PASS。
  - **3.1.5** 提交 `feat(calc): ir_agent snapshot/task ORM + migration`。

- [x] **3.2 测算状态机执行器 + 轮询 + 校验**
  - **3.2.1** 编写 `tests/test_calc_engine.py`：注入 mock FeishuClient，正常路径 created→…→completed；`API_META` 首次 computing 再 done 且 request_id 匹配才读 output；request_id 不匹配 → 不读且判可重试；轮询间隔/超时从配置读取。
  - **3.2.2** 运行 pytest，Expected: FAIL。
  - **3.2.3** 实现 `service/feishu_calc_engine.py`（状态机、`asyncio` 轮询 3s/10s 可配、request_id/参数hash 校验）。
  - **3.2.4** 运行 pytest，Expected: PASS。
  - **3.2.5** 提交 `feat(calc): calculation state machine with polling & validation`。

- [x] **3.3 智能重试策略**
  - **3.3.1** 编写 `tests/test_retry_policy.py`：可重试错误（超时/5xx/429/等算超时/request_id 不匹配）复用同副本重试至多 3 次后 failed 且带 request_id；不可重试（401/403/模板缺失/接口区损坏/参数非法）直接 failed 不重试。
  - **3.3.2**→**3.3.4** 运行失败 → 实现 `service/retry_policy.py` 并接入引擎 → 通过。
  - **3.3.5** 提交 `feat(calc): smart retry policy (retryable vs non-retryable)`。

- [x] **3.4 7 类快照持久化 + report_snapshot 组装**
  - **3.4.1** 编写 `tests/test_snapshot_service.py`：一次成功测算落 7 类快照且不覆盖历史；`report_snapshot` 含环形图（首年各收益）与折线图（15 年序列）底层数值；仅凭 report_snapshot 可重建结果三模块。
  - **3.4.2**→**3.4.4** 运行失败 → 实现 `service/snapshot_service.py`（写 7 表 + 组装 report_snapshot）→ 通过。
  - **3.4.5** 提交 `feat(calc): 7-class snapshot persistence + report_snapshot assembly`。

- [x] **3.5 测算接口（发起/状态/结果）**
  - **3.5.1** 编写 `tests/test_calc_api.py`：`POST /ir/calc/tasks` 返回 `{task_id,version}`；`GET /ir/calc/tasks/{id}` 返回状态流转；`GET /ir/calc/tasks/{id}/result` 返回 report_snapshot；同会话多次测算 version 递增不覆盖。
  - **3.5.2**→**3.5.4** 运行失败 → 实现 `modules/calc/router.py`（异步任务触发引擎 + 状态查询 + 结果读取）→ 通过。
  - **3.5.5** 提交 `feat(calc): task create/status/result endpoints`。
  - **Interfaces**: Produces 三个测算接口 — 被 Batch 4 消费。

## 4. Batch 4：首页对话与结果三模块

依赖：Batch 1、Batch 3。

- [x] **4.1 对话首页视图 + 最小三项抽取**
  - **4.1.1** 编写 `tests/home.spec.js`：输入"测算甘肃 200MW/800MWh"抽取到省份/容量/功率并可发起；输入"测算甘肃储能项目"提示补充功率/容量且不发起。
  - **4.1.2**→**4.1.4** 运行失败 → 实现 `views/home/index.vue`（借鉴 fullscreen-chat 消息流）+ 抽取逻辑 → 通过。
  - **4.1.5** 提交 `feat(frontend): home conversation view + min-input extraction`。

- [x] **4.2 发起→轮询→拉结果 前端链路**
  - **4.2.1** 编写 `tests/calc-flow.spec.js`：mock `api/calc.js`，发起得到 task_id → 轮询状态直至 completed → 拉 result；failed 展示原因与 request_id。
  - **4.2.2**→**4.2.4** 运行失败 → 实现 `api/calc.js` 与轮询编排 → 通过。
  - **4.2.5** 提交 `feat(frontend): calc submit-poll-result orchestration`。

- [x] **4.3 结果三模块 inline 卡片**
  - **4.3.1** 编写 `tests/result-cards.spec.js`：给定 report_snapshot 断言基本信息（节点缺省不显示）、财务指标 5 项、进阶图形容器渲染；断言电价显示 4 位小数、整数不显示小数点、其余非整数显示 2 位小数，且不修改原始数据。
  - **4.3.2**→**4.3.4** 运行失败 → 实现 `components/ResultCards.vue`（`.xc-*` 卡片）与统一展示格式化函数 → 通过。
  - **4.3.5** 提交 `feat(frontend): result three-module inline cards`。

- [x] **4.4 环形图 + 折线图**
  - **4.4.1** 编写 `tests/charts.spec.js`：断言环形图 series 为首年各收益六类、折线图 series 为四条 15 年序列，配色取自 CHARTS.md token。
  - **4.4.2**→**4.4.4** 运行失败 → 实现 `RingChart.vue`、`CashflowLineChart.vue`（ECharts + `design-system/CHARTS.md`）→ 通过。
  - **4.4.5** 提交 `feat(frontend): revenue ring chart + 15y cashflow line chart`。

- [x] **4.5 版本记录列表 + 生成报告占位**
  - **4.5.1** 编写 `tests/version-list.spec.js`：多版本按序展示、最新标记、点击切换查看对应快照；"生成报告"点击提示后续开放不报错。
  - **4.5.2**→**4.5.4** 运行失败 → 实现 `VersionList.vue` + 占位按钮 → 通过。
  - **4.5.5** 提交 `feat(frontend): version list + report placeholder entry`。

- [ ] **4.6 历史会话列表、回放与软删除**
  - **4.6.1** 编写 `agent-backend/tests/db/test_conversation_history_api.py`：断言列表只返回当前用户且未删除会话并按最新活动倒序；详情按固定顺序返回消息、任务版本及 report_snapshot；删除仅写 `deleted_at` 且消息/任务/快照仍存在；其他用户访问列表外会话、详情、删除及 task status/result 均返回 404。
  - **4.6.2** 运行该测试，Expected: FAIL（无 `deleted_at`、历史接口和 task 归属校验）。
  - **4.6.3** 修改 `infrastructure/persistence/orm.py` 并创建 Alembic 迁移增加 `ir_conversation.deleted_at`；实现 `application/conversation_history_service.py` 和 `interface/router.py` 的 `GET /ir/conversations`、`GET /ir/conversations/{conversationId}`、`DELETE /ir/conversations/{conversationId}`；为现有 task status/result 查询增加 `task → conversation → user_id` 归属校验。
  - **4.6.4** 运行后端测试，Expected: PASS；确认软删除后所有快照行数不变。
  - **4.6.5** 编写 `agent-frontend/tests/conversation-history.spec.js`：断言左侧“投资分析工作台”功能项全部排在历史会话之前；首页刷新仍为欢迎页；点击历史项回放固定顺序消息、版本和结果且不调用测算接口；回放后提交携带 `conversation_id`；“…”菜单删除需确认，取消不请求、确认后调用 DELETE 并从列表隐藏。
  - **4.6.6** 运行该测试，Expected: FAIL（无历史列表和回放动作）。
  - **4.6.7** 修改 `AppSidebar.vue`、`api/calc.js`、`store/modules/calculation.js` 与布局挂载逻辑：按原型采用功能导航 → 分隔线 → 历史标题 → 单行省略历史项；进入时仅加载列表；点击详情重建 messages/versions/selectedVersion/conversationId；更多菜单用 Element Plus 二次确认软删除。
  - **4.6.8** 运行 Batch 4 前端全量测试与 `npm run build`，Expected: PASS；手动验证两名用户互不可见、刷新不自动打开、历史回放不访问飞书。
  - **Interfaces**: Consumes 平台 `get_current_user`、Batch 3 快照表；Produces 三个会话历史 API 和可继续追加版本的恢复态 store。
  - **Files**: `Modify: persistence/orm.py, interface/router.py, AppSidebar.vue, store/modules/calculation.js, api/calc.js`; `Create: migration, conversation_history_service.py, test_conversation_history_api.py, conversation-history.spec.js`。

## 5. Batch 5：参数调整与重新测算

依赖：Batch 4（包含 4.6 历史会话回放）。

- [ ] **5.1 inline 调整区（收起/滑块/下拉/分区）**
  - **5.1.1** 编写 `tests/param-adjust.spec.js`：默认收起、展开后按四区渲染、数值用滑块（vue-slider-component）、枚举用下拉；充电成本/放电返还/损耗费用不在调整区重复。
  - **5.1.2**→**5.1.4** 运行失败 → 实现 `components/ParamAdjustPanel.vue`（消费 `GET /ir/calc/param-dict`）→ 通过。
  - **5.1.5** 提交 `feat(frontend): inline parameter adjustment panel`。

- [ ] **5.2 锁项规则（省份永久锁 / 首次锁 / 二次解锁）**
  - **5.2.1** 编写测试：省份在所有版本中只读；首次节点/功率/容量只读、其余按 G 列；二次节点/功率/容量解锁；项目运营期固定15年、换电成本固定0、贷款年限不展示。
  - **5.2.2**→**5.2.5** 运行失败 → 实现锁项逻辑 → 通过 → 提交 `feat(frontend): province permanent lock / first-calc lock / re-calc unlock rules`。

- [ ] **5.3 收益类按表2显隐**
  - **5.3.1** 编写测试：表2现货1/调频1/中长期0/租赁0时展示现货/调频、不展示中长期/租赁；`switch_spot=0` 时现货也不展示；换省必须新建会话。
  - **5.3.2**→**5.3.5** 运行失败 → 扩展 `GET /ir/calc/param-dict?province=` 返回市场开关并实现统一显隐 → 通过 → 提交 `feat(frontend): revenue-type conditional visibility by table2`。

- [ ] **5.4 受控参数覆盖 + 现货依赖判断 + 新版本**
  - **5.4.1** 编写后端测试：`param_overrides` 仅接受 G=1可写输入；省份不可覆盖；节点/容量/功率/日循环任一变化时重新调用 spot 查表并覆盖价格对；依赖不变时不调用 spot，继承上一 input_snapshot 价格对并应用单边/双边手工价格；V3 在依赖不变时继承 V2 手工价；`switch_spot=0` 不查库。
  - **5.4.2** 运行后端测试，Expected: FAIL（当前 task 请求无 overrides、历史详情不暴露 input snapshot）。
  - **5.4.3** 扩展 `TaskCreateReq.param_overrides`、ParamAssembler/TaskService 的受控覆盖与现货依赖策略；会话详情版本返回本次 input_snapshot `apiInput`，供历史回放面板作为版本基线。
  - **5.4.4** 运行后端测试，Expected: PASS；断言 hash 与 input_snapshot 使用最终冻结值，现有单位/换算代码无改动。
  - **5.4.5** 编写前端测试：调整面板提交当前完整值和 `conversation_id`，得到 V2 后保留V1并追加版本；V3从V2 input基线初始化。
  - **5.4.6** 实现 store `recalculate` 复用任务轮询/拉结果编排，运行 Batch5 与历史回归测试，Expected: PASS。
  - **Interfaces**: Extends `POST /ir/calc/tasks` with optional `param_overrides`; consumes previous version `input_snapshot.payload.apiInput`; produces frozen V2/V3 input and report snapshot.

---

## 7. Batch 7：固定 Bearer Token 接口访问控制

依赖：现有应用工厂与统一请求层。

- [ ] **7.1 固定 Token 校验与前端注入**
  - 后端：`IR_API_TOKEN` 配置、全局中间件、`OPTIONS`/health/docs/redoc/openapi 匿名白名单、401 响应壳、`WWW-Authenticate`、恒定时间比较、脱敏失败日志及 OpenAPI Bearer 方案。
  - 前端：`VITE_API_TOKEN` 请求拦截器注入；未配置时不阻止启动；401 使用固定 Token 授权失败文案。
  - 测试：后端覆盖白名单、错误分支、有效 Token、OpenAPI 与日志脱敏；前端覆盖请求头注入与 401 提示；执行相关回归和构建。

---

## 挂账/占位（不在本批次实现，随任务标注）
- 电价库"96点→均价"算法：以接口 stub 注入，PoC 后接真实实现（PRD 挂账 #6）。
- 表2 两档收益（2h/4h）公式：`param_assembler` 留占位与开关，业务确认后补齐（挂账 #3）。
- 底稿 sheet 命名、接口区单元格地址：`param_dict.json` 标注"待业务校对"，冻结后再开发写入（挂账 #5/#7）。
- 报告本体：仅“生成报告”占位入口与版本记录。
- 历史会话回放消息与结果的稳健关联：当前按 assistant 消息位置配对版本；若未来持久化非结果 assistant 消息，需改为 message/task 显式关联（挂账 #14）。
- 现货电价单位契约（已于2026-07-15确认）：预计算表以元/MWh存储，`PrecomputeSpotPriceAlgo` `/1000` 后输出元/kWh，飞书底稿 D39/D40 与参数字典现货字段均为元/kWh；无需改代码。
### 代码评审新增（2026-07-06，Batch3 回顾）
- **平台身份 `allow_anonymous=False` 当前不拦截（挂账 #9）**：`PlatformIdentityMiddleware` 在"禁匿名且无身份 header"时仍放行（`user_id=None`），未返回 401/403。当前默认 `allow_anonymous=true`（联调态）故不暴露；接平台/网关真实鉴权（并绑挂账 #8）前，需补：禁匿名分支显式返回 401。
- **Nacos 装载结果未被消费（挂账 #10）**：`init_nacos_config` 把远端配置写入 `_nacos_cache`，但 `get_settings()` 从不合并该缓存 —— 启用 Nacos 等于静默空操作。接 Nacos 真配前，需补：`get_settings` 合并 `_nacos_cache`（或删除未用的缓存装载路径）。
- **飞书副本幂等 / 孤儿清理（挂账 #11）**：`copy_template` 回执丢失（网络 ACK loss）时，客户端无法区分"未建成"与"建成但回执丢"，会遗留孤儿副本。重试层已消除"每次抖动都新建副本"的泄漏（副本归属上移、串行复用同副本），仅剩此分布式固有边缘。接 `HttpFeishuGateway` 时三选一：① copy 改 find-or-create（按 `request_id` 给副本命名，串行重试先搜后建）；② 定时 GC 清理"无完成任务对应"的副本；③ 接受偶发孤儿 + 记 `request_id` 人工清。

### 现货电价库（2026-07 接真库后新增）
- **现货均价离线预计算日更（挂账 #12，进行中）**：实时算一次 ~23s（取数 16s + DP 7s），不能放同步 assemble。改为离线日更预算表 + 测算时快速查表。见本轮设计讨论。
- **省级修正系数热更新（挂账 #13）**：`spot_price.province_price_coefficients` 改 yml 后，希望**热更新**生效（不重启进程）。当前 `get_settings()` 有 `@lru_cache`、系数在进程启动时定格；且 `RealSpotPriceAlgo._CACHE` 的 key 未含系数。实现预计算日更时一并讨论：系数**不进预算表**（预算表存原始价格 sum，元/MWh），系数在**查询时**应用，天然支持热更；查询侧读系数走可重载配置。
