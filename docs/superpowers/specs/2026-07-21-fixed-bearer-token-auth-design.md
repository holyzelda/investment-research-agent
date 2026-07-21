# 固定 Bearer Token 接口鉴权设计

**日期：** 2026-07-21  
**状态：** 已确认，待实施

## 目标与范围

为朱雀投研智能体增加长期保留的接口访问控制：所有调用方共用一枚固定、全局、不会自动过期的 Bearer Token。它用于确认调用方可以访问接口，不代表用户身份。

范围内：

- 后端统一校验 `Authorization: Bearer <token>`；
- Vue 前端从 `VITE_API_TOKEN` 构建变量读取同一 Token，并由统一请求层自动附带；
- 其他平台调用方按约定自行附带该 Token；
- Swagger/OpenAPI 提供 Bearer 授权交互；
- 需求、执行制品、工程约束与自动化测试同步更新。

范围外：登录、注册、JWT、会话、过期、刷新、Token 轮换/撤销、多 Token、RBAC、用户级权限与前端登录页。

## 架构

新增后端 `FixedTokenAuthMiddleware`，作为唯一的接口访问令牌校验点。它独立于平台身份中间件、业务路由和持久化层。

```text
调用方
  → FixedTokenAuthMiddleware
      → RequestLoggingMiddleware
      → PlatformIdentityMiddleware
      → 路由与业务服务
```

中间件放行以下匿名请求：

- 任意 `OPTIONS` CORS 预检；
- `GET /health`；
- `GET /docs`；
- `GET /redoc`；
- `GET /openapi.json`。

其他请求必须携带严格格式的 `Authorization: Bearer <token>`。服务端将收到的 Token 与配置 Token 用 `hmac.compare_digest` 比较。`IR_API_TOKEN` 未配置时，所有受保护请求同样拒绝，绝不回退为匿名放行。

通过鉴权后，既有平台身份中间件继续读取 `X-User-Id` / `X-User-Name`。请求缺少身份 header 时，保持既有匿名用户逻辑；固定 Token 不替代用户身份。

## 配置与前端集成

后端新增 `ApiAuthConfig.token`，按以下优先级取值：

1. 环境变量 `IR_API_TOKEN`；
2. `configs/application.yml` 的 `api_auth.token`；
3. 空字符串默认值。

真实 Token 必须在部署环境变量中配置，不能提交到仓库。

前端统一 Axios 请求拦截器读取 `VITE_API_TOKEN`。有值时自动追加 `Authorization: Bearer <token>`；无值时不追加、不阻止应用启动，并仅在开发环境输出一次不含敏感信息的警告。真实值放在 Git 忽略的 `agent-frontend/.env.local`，构建产物仍会包含该 Token，这是共享浏览器调用凭据方案的已知边界。

未来接入反向代理或网关时，代理可以注入同一 Token，但后端保持本鉴权中间件并持续校验；前端是否继续注入由部署方案决定，不改变接口契约。

## 错误处理与日志

以下任一情况返回相同结果：Token 缺失、Bearer 格式错误、Token 不匹配、服务端 Token 未配置。

- HTTP 状态：`401`；
- 响应头：`WWW-Authenticate: Bearer`；
- 响应体：`{"code": 401, "msg": "未授权访问", "data": null}`。

中间件为失败请求写一条 warning 日志，仅含方法、路径、客户端 IP 与失败类别（`missing`、`invalid_format`、`invalid_token` 或 `server_not_configured`）。日志和通用请求日志均不得记录 Authorization 的值。

前端将 401 呈现为固定 Token 配置或授权失败的通用错误，不再误称为平台登录状态失效。

## OpenAPI

FastAPI OpenAPI schema 定义 HTTP Bearer 安全方案；受保护业务操作默认引用该方案。Swagger UI 显示 **Authorize**，填入 Token 后，Try it out 自动附带 Authorization。白名单文档端点本身仍允许匿名读取。

## 验证

后端 pytest 覆盖：

- 全部匿名白名单和 OPTIONS 放行；
- 缺失、格式错误、错误 Token、服务端未配置 Token 的 401 响应体和 `WWW-Authenticate`；
- 正确 Token 可访问业务接口；
- OpenAPI 的 Bearer 定义与受保护接口安全要求；
- 鉴权失败日志不含原始 Token。

前端 Vitest 覆盖：

- 配置 `VITE_API_TOKEN` 时请求拦截器添加正确 Authorization；
- 未配置时不添加 Authorization；
- 401 提示遵循固定 Token 语义。

实施完成后运行相关后端 pytest、前端 Vitest 全量测试与 `pnpm build`。
