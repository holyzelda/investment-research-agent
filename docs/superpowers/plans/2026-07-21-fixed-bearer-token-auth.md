# 固定 Bearer Token 接口鉴权 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为所有后端业务接口提供长期固定 Bearer Token 校验，并让 Vue 统一请求层自动携带同一共享 Token。

**Architecture:** 后端新增独立的 `FixedTokenAuthMiddleware`，在请求日志和平台身份读取之前执行，默认保护所有请求，仅放行 CORS 预检、健康检查及文档端点。前端保留现有 Axios 单例，在请求拦截器中从构建变量读取 Token；身份 header 的归属逻辑保持不变。

**Tech Stack:** Python 3.13、FastAPI/Starlette、Pydantic、httpx/pytest、Vue 3、Vite、Axios、Vitest。

## Global Constraints

- 使用一枚全局、固定、不会自动过期的 `Authorization: Bearer <token>`；不新增登录、注册、JWT、session、刷新、轮换、撤销、RBAC 或用户权限。
- 服务端真实 Token 仅通过 `IR_API_TOKEN` 部署环境变量配置，不能提交到仓库；未配置时受保护请求必须拒绝。
- 前端真实 Token 仅通过被 Git 忽略的 `agent-frontend/.env.local` 中的 `VITE_API_TOKEN` 配置；它是共享调用方凭据，不是用户登录 Token，构建产物可见是已知边界。
- 匿名白名单仅为 `OPTIONS *`、`GET /health`、`GET /docs`、`GET /redoc`、`GET /openapi.json`。
- 其他缺失、格式错误、错误或服务端未配置 Token 的请求统一返回 HTTP 401、`WWW-Authenticate: Bearer` 与 `{code: 401, msg: "未授权访问", data: null}`。
- 比较必须使用 `hmac.compare_digest`；日志绝不写 Authorization 原文。
- 有效 Token 但无平台身份 header 的请求仍遵循既有匿名用户规则。
- 不新增第三方依赖；后端只通过 `requirements.txt` 管理依赖，前端只使用 pnpm。
- 所有 Python 命令使用 `.venv\Scripts\python.exe`；pytest 使用 `sys.stdout = sys.stderr` 包装器。
- 不执行任何 Git 写操作（`git add`、`git commit`、`git push`）；由用户自行处理提交。

---

## File Structure

| 文件 | 变更 | 责任 |
|---|---|---|
| `D:/0_工作/2026/投研智能体/docs/prd/PRD-001.md` | 修改 | 将固定 Bearer Token 作为长期接口访问控制需求，保持登录/JWT/RBAC 范围外。 |
| `changes/PRD-001-login-calc-mainflow/execution-contract.md` | 修改 | 将 token 校验从范围外改为已批准的独立能力，并加入验收条件。 |
| `changes/PRD-001-login-calc-mainflow/tasks.md` | 修改 | 新增固定 Token 鉴权任务与测试交付物。 |
| `changes/PRD-001-login-calc-mainflow/.superpowers/sdd/execution-plan.json` | 修改 | 修订执行计划波次，使鉴权任务在现有批次之后可追踪。 |
| `agent-backend/app/core/config/settings.py` | 修改 | 定义 `ApiAuthConfig`，按 `IR_API_TOKEN > application.yml > ""` 解析。 |
| `agent-backend/configs/application.yml` | 修改 | 提供空 `api_auth.token` 示例，不能填真实值。 |
| `agent-backend/app/infrastructure/web/middleware/fixed_token_auth.py` | 新建 | 白名单、Bearer 格式解析、恒定时间比较、401 响应与脱敏审计日志。 |
| `agent-backend/app/infrastructure/web/app_factory.py` | 修改 | 注册鉴权中间件、声明 OpenAPI Bearer 安全方案、设置业务操作默认安全要求。 |
| `agent-backend/tests/e2e/test_fixed_token_auth.py` | 新建 | 验证白名单、401 契约、配置缺失、有效 Token、OpenAPI 方案和日志脱敏。 |
| `agent-frontend/src/utils/request.js` | 修改 | 使用 `VITE_API_TOKEN` 注入 Authorization，并更新 401 文案。 |
| `agent-frontend/tests/request-auth.spec.js` | 新建 | 验证 Axios 请求头注入、缺省行为和 401 提示。 |
| `agent-frontend/.env.example` | 新建或修改 | 只展示空 `VITE_API_TOKEN`，不含真实值。 |
| `agent-frontend/CLAUDE.md` | 修改 | 为固定接口访问 Token 增加环境变量例外，仍禁止用户登录 token 与路由守卫。 |
| `agent-frontend/vite.config.js` | 修改 | 更新注释，说明前端可读取固定接口 Token，但不承载业务登录配置。 |
| `CLAUDE.md`、`agent-backend/CLAUDE.md` | 修改 | 将“无 token 二次校验”改为固定接口 Token 校验与平台身份读取并存。 |

---

### Task 1: 更新权威需求、执行合同与工程约束

**Files:**
- Modify: `D:/0_工作/2026/投研智能体/docs/prd/PRD-001.md:21-24, 125-133, 321-329, 334-343`
- Modify: `changes/PRD-001-login-calc-mainflow/execution-contract.md:19-25, 31-49, 51-58, 104-108`
- Modify: `changes/PRD-001-login-calc-mainflow/tasks.md:45-49, 246-263`
- Modify: `changes/PRD-001-login-calc-mainflow/.superpowers/sdd/execution-plan.json`
- Modify: `CLAUDE.md:项目定位、跨端铁律`
- Modify: `agent-backend/CLAUDE.md:Architecture`
- Modify: `agent-frontend/CLAUDE.md:7-10, 32-50`
- Modify: `agent-frontend/vite.config.js:8-10`

**Interfaces:**
- Consumes: 已确认设计 `docs/superpowers/specs/2026-07-21-fixed-bearer-token-auth-design.md`。
- Produces: 允许后续中间件、前端构建变量和测试实现的正式 PRD、执行合同及工程约束。

- [ ] **Step 1: 把 PRD 的平台接入边界改为“平台身份 + 固定接口 Token”双层职责**

  在 `PRD-001.md` 的平台接入说明中，将“不做 token 二次校验”的表述替换为以下规则：

  ```markdown
  3. **接口访问控制与身份传递**：本系统长期维护一枚全局固定 Bearer Token，调用方必须通过 `Authorization: Bearer <token>` 访问受保护接口；该 Token 只确认调用方可以访问接口，不代表用户身份。平台/网关注入的 `user_id`、`username` header 仍只用于会话和快照归属；缺失时按后端既有匿名策略处理。
     - 固定 Token 不自动过期、不刷新、不实现多 Token、轮换、撤销、JWT 或 RBAC；真实值由部署环境配置。
     - `OPTIONS`、`GET /health`、`GET /docs`、`GET /redoc`、`GET /openapi.json` 不要求该 Token；其他接口缺失、格式错误或不匹配时返回统一 401 响应壳。
  ```

  在技术约束、范围内/范围外段落同步写明：`IR_API_TOKEN` 是服务端配置，`VITE_API_TOKEN` 是前端构建变量，且二者是同一共享调用方凭据；不把它描述为登录或用户认证。

- [ ] **Step 2: 更新 execution contract 与任务台账**

  在 `execution-contract.md`：

  - 从“范围外”移除 `token 二次校验`；
  - 在 Approved Behavior 表新增“固定接口 Token 鉴权”行，写明白名单、401、OpenAPI、前端统一注入和测试；
  - 在 Design Constraints 增加“固定 Token 与平台身份 header 职责独立”；
  - 在验证要求增加后端与前端鉴权测试。

  在 `tasks.md` 末尾新增一个完成条件明确的任务段落：

  ```markdown
  ## Batch 7：固定 Bearer Token 接口访问控制

  - [ ] **7.1 固定 Token 校验与前端注入**
    - 后端：`IR_API_TOKEN` 配置、全局中间件、匿名白名单、401 响应壳、`WWW-Authenticate`、恒定时间比较、脱敏失败日志及 OpenAPI Bearer 方案。
    - 前端：`VITE_API_TOKEN` 请求拦截器注入；未配置时不阻止启动；401 使用固定 Token 授权失败文案。
    - 测试：后端覆盖白名单、错误分支、有效 Token、OpenAPI 与日志脱敏；前端覆盖请求头注入与 401 提示；执行相关回归和构建。
  ```

- [ ] **Step 3: 修订执行计划 JSON**

  将 `execution-plan.json` 的 `revision` 加一；新增 `auth` 波次，其任务顺序必须是 `requirements-and-constraints` → `backend-auth` → `frontend-auth` → `verification`。更新 `artifacts_hash`、`contract_hash`、`hash` 与 `recommendation_receipt` 为本次制品重新生成的值；不得保留旧 hash 伪装为新制品。

- [ ] **Step 4: 修订各 CLAUDE 指令以消除矛盾**

  - 根 `CLAUDE.md`：将“本系统不实现 token 校验”替换为“不实现用户登录/JWT/RBAC；固定接口 Token 校验是例外”。
  - 后端 `CLAUDE.md`：在 platform_access 描述后补充“固定接口访问校验在 web 中间件完成，平台身份中间件不处理 Token”。
  - 前端 `CLAUDE.md`：将“前端不管理任何登录 token”保留，并补充“允许唯一的 `VITE_API_TOKEN` 作为共享固定接口访问 Token，不得将它扩展为用户登录态”；将环境变量允许项从四项改为五项并注明真实值仅 `.env.local`；把 401 描述改为固定 Token 配置/授权失败。
  - `vite.config.js` 仅更新注释：`VITE_API_TOKEN` 是请求层消费的固定访问凭据，不在 Vite proxy 内处理。

- [ ] **Step 5: 审阅需求制品一致性**

  手工检查所有修改后的文档，确认每一处都同时满足以下断言：

  ```text
  固定 Token 是长期接口访问控制；
  Token 不是平台用户身份；
  平台身份 header 仍用于归属；
  不引入登录/JWT/RBAC；
  白名单与 401 契约完全一致。
  ```

  Expected: 不存在“token 二次校验范围外”“前端不能使用 VITE_API_TOKEN”或“401 必为平台登录失效”的冲突表述。

---

### Task 2: 后端配置与固定 Token 鉴权中间件

**Files:**
- Modify: `agent-backend/app/core/config/settings.py:74-165, 168-255`
- Modify: `agent-backend/configs/application.yml:25-36`
- Create: `agent-backend/app/infrastructure/web/middleware/fixed_token_auth.py`
- Modify: `agent-backend/app/infrastructure/web/app_factory.py:1-64`
- Test: `agent-backend/tests/e2e/test_fixed_token_auth.py`

**Interfaces:**
- Consumes: `get_settings().api_auth.token: str` and the existing `{code,msg,data}` response convention.
- Produces: `FixedTokenAuthMiddleware` and `ApiAuthConfig`; requests reaching routers have passed token validation unless they match the anonymous whitelist.

- [ ] **Step 1: 编写后端失败测试**

  新建 `tests/e2e/test_fixed_token_auth.py`。测试通过 `monkeypatch.setenv("IR_API_TOKEN", "test-fixed-token")` 后调用 `reload_settings()`，再以 `create_app()` 建立独立 app。使用 `httpx.ASGITransport` 和 `AsyncClient`。

  写入以下测试：

  ```python
  @pytest.mark.asyncio
  @pytest.mark.parametrize(
      ("method", "path"),
      [
          ("OPTIONS", "/ir/me"),
          ("GET", "/health"),
          ("GET", "/docs"),
          ("GET", "/redoc"),
          ("GET", "/openapi.json"),
      ],
  )
  async def test_anonymous_whitelist_is_available(client, method, path):
      response = await client.request(method, path)
      assert response.status_code == 200

  @pytest.mark.asyncio
  @pytest.mark.parametrize(
      "authorization",
      [None, "Token test-fixed-token", "Bearer", "Bearer wrong-token"],
  )
  async def test_invalid_authorization_returns_standard_401(client, authorization):
      headers = {} if authorization is None else {"Authorization": authorization}
      response = await client.get("/ir/me", headers=headers)
      assert response.status_code == 401
      assert response.headers["www-authenticate"] == "Bearer"
      assert response.json() == {"code": 401, "msg": "未授权访问", "data": None}

  @pytest.mark.asyncio
  async def test_valid_authorization_reaches_platform_route(client):
      response = await client.get("/ir/me", headers={"Authorization": "Bearer test-fixed-token"})
      assert response.status_code == 200
  ```

  再增加：清空 `IR_API_TOKEN` 后 `/ir/me` 带任意 Bearer 仍是同一 401；`/openapi.json` 包含 `components.securitySchemes.FixedBearerAuth` 与 `/ir/me` GET 的 `security: [{"FixedBearerAuth": []}]`；使用 `caplog` 或 Loguru sink 捕获失败日志，断言日志包含 `invalid_token` 但不包含传入的秘密字符串 `do-not-log-this-token`。

- [ ] **Step 2: 运行测试确认失败**

  从 `agent-backend/` 执行：

  ```bash
  .venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/e2e/test_fixed_token_auth.py', '-q', '-o', 'asyncio_mode=auto']))"
  ```

  Expected: FAIL，因为 `ApiAuthConfig` 和 `FixedTokenAuthMiddleware` 尚不存在，且 `/ir/me` 未要求 Authorization。

- [ ] **Step 3: 增加配置模型与 YAML 空示例**

  在 `settings.py` 定义：

  ```python
  class ApiAuthConfig(BaseModel):
      """固定 Bearer Token 接口访问控制配置。"""
      token: str = ""
  ```

  将 `api_auth: ApiAuthConfig = ApiAuthConfig()` 加入 `Settings`。在 `_build_settings()` 中添加：

  ```python
  api_auth = ApiAuthConfig(
      token=os.getenv("IR_API_TOKEN", _nested(y, ["api_auth", "token"], "")),
  )
  ```

  并在返回值中传入 `api_auth=api_auth`。

  在 `configs/application.yml` 的 `platform` 与 `cors` 之间添加：

  ```yaml
  api_auth:
    # 固定 Bearer Token；真实值使用部署环境变量 IR_API_TOKEN 注入，禁止提交。
    token: ""
  ```

- [ ] **Step 4: 实现最小的中间件**

  新建 `fixed_token_auth.py`，实现如下结构：

  ```python
  """固定 Bearer Token 接口访问控制中间件。"""
  import hmac

  from loguru import logger
  from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
  from starlette.requests import Request
  from starlette.responses import JSONResponse, Response

  from app.core.config.settings import get_settings

  _ANONYMOUS_GET_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}


  class FixedTokenAuthMiddleware(BaseHTTPMiddleware):
      async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
          if request.method == "OPTIONS" or (
              request.method == "GET" and request.url.path in _ANONYMOUS_GET_PATHS
          ):
              return await call_next(request)

          configured_token = get_settings().api_auth.token
          authorization = request.headers.get("Authorization")
          failure = self._failure_reason(authorization, configured_token)
          if failure is not None:
              self._log_failure(request, failure)
              return JSONResponse(
                  status_code=401,
                  content={"code": 401, "msg": "未授权访问", "data": None},
                  headers={"WWW-Authenticate": "Bearer"},
              )
          return await call_next(request)

      @staticmethod
      def _failure_reason(authorization: str | None, configured_token: str) -> str | None:
          if not configured_token:
              return "server_not_configured"
          if not authorization:
              return "missing"
          scheme, separator, token = authorization.partition(" ")
          if scheme != "Bearer" or separator != " " or not token or token.strip() != token:
              return "invalid_format"
          if not hmac.compare_digest(token, configured_token):
              return "invalid_token"
          return None

      @staticmethod
      def _log_failure(request: Request, failure: str) -> None:
          client_ip = request.client.host if request.client else "unknown"
          logger.warning(
              "固定接口 Token 鉴权失败 "
              f"reason={failure} method={request.method} path={request.url.path} client_ip={client_ip}"
          )
  ```

  不在此文件输出 `authorization` 或 `token`；不增加开关、多 Token、令牌解析或外部存储。

- [ ] **Step 5: 将中间件注册为最外层，并配置 OpenAPI Bearer 方案**

  在 `app_factory.py`：

  1. 导入 `HTTPBearer` 与 `get_openapi`，导入新中间件。
  2. 新增 `_custom_openapi(app: FastAPI) -> dict`，在生成 schema 后写入：

     ```python
     schema.setdefault("components", {}).setdefault("securitySchemes", {})["FixedBearerAuth"] = {
         "type": "http",
         "scheme": "bearer",
         "bearerFormat": "Token",
         "description": "固定接口访问 Token。请输入 Token 原文，Swagger 会按 Bearer 方案发送。",
     }
     for path, operations in schema.get("paths", {}).items():
         if path in {"/health", "/docs", "/redoc", "/openapi.json"}:
             continue
         for operation in operations.values():
             if isinstance(operation, dict):
                 operation["security"] = [{"FixedBearerAuth": []}]
     ```

  3. `create_app()` 创建 app 后设置：

     ```python
     app.openapi = lambda: _custom_openapi(app)
     ```

     `_custom_openapi` 必须先判断并复用 `app.openapi_schema`，防止每次请求重建。

  4. 按 Starlette “后添加先执行”规则，保证固定 Token 鉴权先于日志和平台身份：

     ```python
     app.add_middleware(PlatformIdentityMiddleware)
     app.add_middleware(RequestLoggingMiddleware)
     app.add_middleware(FixedTokenAuthMiddleware)
     ```

     保留 CORS 注册；其添加位置必须使浏览器 OPTIONS 在到达鉴权时已被白名单放行。

- [ ] **Step 6: 运行鉴权测试确认通过**

  ```bash
  .venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/e2e/test_fixed_token_auth.py', '-q', '-o', 'asyncio_mode=auto']))"
  ```

  Expected: PASS，所有白名单 200、无效请求 401、有效 Token 200、OpenAPI Bearer 方案存在且日志没有 Token 原文。

- [ ] **Step 7: 运行相关后端回归**

  ```bash
  .venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/e2e/test_app_boot.py', 'tests/e2e/platform_access/test_identity.py', '-q', '-o', 'asyncio_mode=auto']))"
  ```

  Expected: PASS。若既有平台身份测试直接调用受保护端点，测试客户端必须明确加 `Authorization: Bearer test-fixed-token`，不能通过关闭新鉴权规避。

---

### Task 3: 前端共享 Token 请求注入与用户提示

**Files:**
- Modify: `agent-frontend/src/utils/request.js:1-60`
- Create: `agent-frontend/tests/request-auth.spec.js`
- Create or Modify: `agent-frontend/.env.example`
- Modify: `agent-frontend/CLAUDE.md:32-50`
- Modify: `agent-frontend/vite.config.js:8-10`

**Interfaces:**
- Consumes: Vite build variable `import.meta.env.VITE_API_TOKEN` and existing `service` Axios instance.
- Produces: Every request dispatched through `request.js` includes `Authorization: Bearer <token>` iff the variable is non-empty; missing variable leaves the request unchanged.

- [ ] **Step 1: 写前端失败测试**

  新建 `tests/request-auth.spec.js`。在 import `@/utils/request` 前，通过 `vi.stubEnv` 设置变量；每个 test 后用 `vi.unstubAllEnvs()` 清理。使用 Axios 请求拦截器的 handlers 手动调用已注册 fulfilled 函数，不发真实 HTTP：

  ```javascript
  import { afterEach, describe, expect, it, vi } from 'vitest'

  const requestInterceptor = () => request.interceptors.request.handlers.at(-1).fulfilled

  afterEach(() => {
    vi.unstubAllEnvs()
    vi.restoreAllMocks()
  })

  it('adds the configured fixed bearer token', async () => {
    vi.stubEnv('VITE_API_TOKEN', 'frontend-fixed-token')
    const { default: request } = await import('@/utils/request')

    const config = requestInterceptor()( { headers: {} } )
    expect(config.headers.Authorization).toBe('Bearer frontend-fixed-token')
  })

  it('does not add authorization when the token is absent', async () => {
    vi.stubEnv('VITE_API_TOKEN', '')
    const { default: request } = await import('@/utils/request')

    const config = requestInterceptor()( { headers: {} } )
    expect(config.headers.Authorization).toBeUndefined()
  })
  ```

  为了避免模块缓存造成环境变量取值固定，实现应在拦截器执行时读取 `import.meta.env.VITE_API_TOKEN`；测试使用 `vi.resetModules()` 后重新 import，或从请求模块显式导出 `applyFixedBearerToken(config, token = import.meta.env.VITE_API_TOKEN)` 后直接测试该纯函数。选择后者，函数签名固定为：

  ```javascript
  export function applyFixedBearerToken(config, token = import.meta.env.VITE_API_TOKEN) { /* ... */ }
  ```

  再写一项响应测试：构造 `{ data: { code: 401, msg: '未授权访问' } }` 交给响应 fulfilled handler，mock `ElMessage.error`，断言文案为 `接口访问未授权，请检查固定 Token 配置`，而不是“登录状态异常”。

- [ ] **Step 2: 运行测试确认失败**

  从 `agent-frontend/` 执行：

  ```bash
  pnpm vitest run tests/request-auth.spec.js
  ```

  Expected: FAIL，因为 `applyFixedBearerToken` 尚未导出，且现有 401 文案仍为平台登录状态异常。

- [ ] **Step 3: 实现纯函数和请求拦截器调用**

  在 `src/utils/request.js` 的 Axios 实例下方添加：

  ```javascript
  let hasWarnedMissingApiToken = false

  export function applyFixedBearerToken(config, token = import.meta.env.VITE_API_TOKEN) {
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
      return config
    }

    if (import.meta.env.DEV && !hasWarnedMissingApiToken) {
      console.warn('未配置 VITE_API_TOKEN，后端受保护接口将返回 401')
      hasWarnedMissingApiToken = true
    }
    return config
  }
  ```

  将现有请求拦截器改为：

  ```javascript
  (config) => {
    config.headers['Content-Type'] = config.headers['Content-Type'] || 'application/json;charset=utf-8'
    return applyFixedBearerToken(config)
  }
  ```

  把 401 分支替换为：

  ```javascript
  if (code === 401) {
    ElMessage.error('接口访问未授权，请检查固定 Token 配置')
    return Promise.reject(new Error(msg || '未授权访问'))
  }
  ```

  更新文件顶部注释，区分“固定接口访问 Token”和“用户登录 Token”：前者允许注入，后者仍由平台管理且不在本项目实现。

- [ ] **Step 4: 添加无秘密示例与同步前端约束**

  创建或更新 `agent-frontend/.env.example`：

  ```dotenv
  VITE_APP_BASE_API=/gateway/
  VITE_APP_TITLE=朱雀投研智能体
  VITE_FAVICON=/favicon.ico
  VITE_APP_ENV=development
  # 固定接口访问 Token；真实值只写入被忽略的 .env.local，不能提交。
  VITE_API_TOKEN=
  ```

  在 `agent-frontend/CLAUDE.md` 中把允许变量列表明确更新为五项，并加入：

  ```markdown
  `VITE_API_TOKEN` 是唯一允许的前端凭据：用于共享固定接口访问 Token，不是用户登录 Token，不得用于路由守卫、登录页、刷新机制或用户身份状态。
  ```

  在 `vite.config.js` 的注释中明确这个变量由 `src/utils/request.js` 消费，代理不添加也不校验 Authorization。

- [ ] **Step 5: 运行前端鉴权测试确认通过**

  ```bash
  pnpm vitest run tests/request-auth.spec.js
  ```

  Expected: PASS，正确 Token 加入 Authorization、空 Token 不加入、401 显示固定 Token 授权文案。

- [ ] **Step 6: 运行前端回归与构建**

  ```bash
  pnpm test
  pnpm build
  ```

  Expected: 两个命令均退出码 0。若 `tests/scaffold.spec.js` 仍写死“前端不管理任何 token”，更新断言为“无 login/register/captcha/路由守卫，且只允许 `VITE_API_TOKEN` 固定接口访问凭据”。

---

### Task 4: 全链路验证与交付检查

**Files:**
- Modify only if needed: `agent-backend/tests/e2e/test_fixed_token_auth.py`
- Modify only if needed: `agent-frontend/tests/request-auth.spec.js`
- Review: `docs/superpowers/specs/2026-07-21-fixed-bearer-token-auth-design.md`
- Review: `docs/superpowers/plans/2026-07-21-fixed-bearer-token-auth.md`

**Interfaces:**
- Consumes: Tasks 1–3 的最终实现和测试。
- Produces: 已验证的固定 Bearer Token 鉴权变更，且不含真实 Token、无范围外功能。

- [ ] **Step 1: 执行后端全量测试**

  从 `agent-backend/` 执行：

  ```bash
  .venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['-q', '-o', 'asyncio_mode=auto']))"
  ```

  Expected: PASS。若失败，先判断失败的测试是否直接调用了受保护业务端点；只为该测试提供 `Authorization: Bearer test-fixed-token`，不要放宽中间件白名单或关闭鉴权。

- [ ] **Step 2: 执行前端全量测试与生产构建**

  从 `agent-frontend/` 执行：

  ```bash
  pnpm test
  pnpm build
  ```

  Expected: PASS。确认构建过程没有把实际 `VITE_API_TOKEN` 打印到命令输出。

- [ ] **Step 3: 检查不变量和敏感信息**

  使用内容搜索检查：

  ```text
  1. 不存在提交到仓库的真实 `IR_API_TOKEN=` 或 `VITE_API_TOKEN=` 值；示例必须为空。
  2. 中间件和请求日志中不存在输出 Authorization 原文的格式化代码。
  3. 白名单只含 OPTIONS、health、docs、redoc、openapi.json。
  4. 业务路由不应各自复制 Token 校验。
  5. 没有新增登录页、路由守卫、JWT 依赖、会话表或 RBAC 代码。
  ```

  Expected: 五项均成立。

- [ ] **Step 4: 人工请求验收**

  在后端启动且 `IR_API_TOKEN` 已通过当前 shell 环境设置后，验证：

  ```bash
  curl -i http://127.0.0.1:9089/health
  curl -i http://127.0.0.1:9089/ir/me
  curl -i -H "Authorization: Bearer <IR_API_TOKEN>" http://127.0.0.1:9089/ir/me
  ```

  Expected:

  ```text
  /health → 200；
  无 Authorization 的 /ir/me → 401、WWW-Authenticate: Bearer、标准响应壳；
  正确 Authorization 的 /ir/me → 200，且在身份 header 缺失时仍返回既有匿名用户信息。
  ```

- [ ] **Step 5: 汇总交付，不执行 Git 写操作**

  记录：变更文件、后端 pytest 结果、前端 test/build 结果、任何未执行项及原因。不要执行 `git add`、`git commit` 或 `git push`；由用户决定版本控制操作。

## Plan Self-Review

- **Spec coverage:** Task 1 覆盖 PRD、合同、执行计划及约束；Task 2 覆盖后端配置、中间件、白名单、401、恒定时间比较、脱敏日志、OpenAPI；Task 3 覆盖前端环境变量、自动请求头、缺省行为、401 文案和约束；Task 4 覆盖完整回归、无密钥检查与人工验收。
- **Placeholder scan:** 计划中没有 TBD/TODO/“同上”式指令；每个实现步骤列出了目标文件、函数/字段名、命令与预期结果。
- **Type consistency:** 后端统一使用 `ApiAuthConfig.token`、`get_settings().api_auth.token`、`FixedTokenAuthMiddleware`、`FixedBearerAuth`；前端统一使用 `VITE_API_TOKEN`、`applyFixedBearerToken`；401 契约统一为 HTTP 401 + `WWW-Authenticate: Bearer` + 固定响应壳。
