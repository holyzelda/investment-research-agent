# 朱雀投研智能体 · 前端（agent-frontend）

统一平台的子应用。**无独立登录**：用户在平台首页完成登录后跳转承接，落地本系统对话首页；身份由平台/网关注入后端请求头，前端不管理任何登录 token。

## 技术栈
Vue 3 + Vite 5 + Element Plus + Pinia + Vue Router 4 + ECharts 5 + Tailwind（仅布局）+ 玄策(XC)设计体系。
包管理器统一用 **pnpm**。

---

## 一、前置：确认工具链（只需检查一次）

前端和后端不同——后端用 Python(pip/venv)，**前端用 Node.js + pnpm**，依赖装进 `node_modules/`。

```bash
node -v      # 需要 Node.js（建议 ≥18）。没有就去 https://nodejs.org 装
pnpm -v      # 需要 pnpm。若提示找不到命令，用下面一条命令一次性全局安装：
npm i -g pnpm
```

> **为什么用 pnpm 而不是 npm**：pnpm 更快、用硬链接省磁盘，且本项目锁文件是 `pnpm-lock.yaml`。
> `package.json` 里设了 `preinstall: only-allow pnpm`，**用 npm/yarn 安装会被直接拦截报错**，防止团队装出不一致的依赖。

---

## 二、启动前端（第一次跑，照着做）

```bash
# 1) 进入前端目录
cd D:\1_code\investment-research-agent\agent-frontend

# 2) 安装依赖（装进 node_modules/，只需一次；之后改了 package.json 才重跑）
pnpm install

# 3) 启动开发服务器（热更新；改代码浏览器自动刷新。按 Ctrl+C 停止）
pnpm dev
```

启动成功后，终端会打印类似：

```
  VITE v5.x  ready in xxx ms
  ➜  Local:   http://localhost:5210/
```

**浏览器打开 http://localhost:5210** —— 就能看到"朱雀投研智能体"对话首页（顶栏品牌 + 中间"用一句话给出省份/容量/功率"引导 + 右侧版本记录占位）。

> **每步在做什么**：
> - `pnpm install`：读 `package.json` + `pnpm-lock.yaml`，把依赖下载到 `node_modules/`。这是"装依赖"，相当于后端的 `pip install -r requirements.txt`。
> - `pnpm dev`：启动 Vite 开发服务器（带热更新），把源码即时编译成浏览器能跑的页面。这是"起服务"，相当于后端的 `uvicorn ...`。

---

## 三、前端如何连后端（代理说明）

前端页面里所有 API 请求都发往 `VITE_APP_BASE_API`（见 `.env`，默认 `/gateway/`）。
开发时 Vite 会把 `/gateway/` 的请求**代理**到本地后端：

```
浏览器 → http://localhost:5210/gateway/ir/me  →（Vite 代理）→ http://127.0.0.1:8080/ir/me
```

所以要联调"前端 + 后端"，需**两个终端同时开**：
- 终端 A：后端 `uvicorn app.main:app --reload --port 8080`
- 终端 B：前端 `pnpm dev`

代理目标在 `vite.config.js` 里配（`server.proxy`），后端端口若改了，同步改 `.env` 的 `VITE_DEV_BACKEND`。

> 阶段0 未接平台注入 header，前端 `GET /ir/me` 会拿到后端的**匿名占位**用户（`allow_anonymous=true`），顶栏显示"访客"，属正常。

---

## 四、常用命令

```bash
pnpm install   # 安装依赖（按锁文件还原）
pnpm dev       # 启动开发服务器（http://localhost:5210）
pnpm test      # 跑单元测试（vitest）
pnpm build     # 生产构建，产物在 dist/
pnpm preview   # 本地预览构建产物
```

---

## 五、目录结构

```
src/
├── design-system/   # 玄策 tokens（视觉基线，禁止内联 hex，一律 var(--xc-*)）
├── styles/          # 全局样式（引入 tokens + 深色基线）
├── utils/request.js # axios 实例（{code,msg,data} 响应壳，无登录 token）
├── store/           # Pinia（session：当前用户来自平台注入 /ir/me）
├── router/          # 路由（无登录守卫，默认落地 /home）
├── layout/          # 顶栏 + 主体布局
├── api/             # 接口封装（session / calc）
└── views/home/      # 对话首页（Batch 4 接入对话消息流与结果三模块）
```

## 六、配置

前端 `.env.*` **只配 4 项**（不含任何后端业务配置）：
- `VITE_APP_BASE_API` — 网关基地址（默认 `/gateway/`）
- `VITE_APP_TITLE` — 页面/品牌标题
- `VITE_FAVICON` — 图标
- `VITE_APP_ENV` — 环境标识

`.env`(通用) / `.env.development` / `.env.production` / `.env.staging` 分环境覆盖。

---

## 七、依赖管理约定

- 统一用 **pnpm**，不搞安装脚本，照上面命令人工执行即可。
- **`pnpm-lock.yaml` 必须提交进 git** —— 它锁定每个依赖的精确版本，是团队环境一致的关键。
- 新增依赖：`pnpm add <包名>` → 提交更新后的 `package.json` + `pnpm-lock.yaml`。
- 删依赖：`pnpm remove <包名>`。
- CI / 要求严格一致时：`pnpm install --frozen-lockfile`（锁文件与 package.json 对不上就报错，不会偷偷改）。

---

## 八、常见问题

| 现象 | 原因 / 解决 |
|---|---|
| `pnpm: command not found` | 没装 pnpm → `npm i -g pnpm` |
| 执行 `npm install` 报 `only allow pnpm` | 正常拦截，改用 `pnpm install` |
| 页面能开但请求 404 / 跨域 | 后端没起，或端口不是 8080 → 起后端，或改 `.env` 的 `VITE_DEV_BACKEND` |
| 顶栏用户显示"访客" | 阶段0 未接平台 header，匿名占位，正常 |
| 端口 5210 被占用 | Vite 会自动换端口，或在 `vite.config.js` 改 `server.port` |
| 装依赖很慢 | 可切国内镜像：`pnpm config set registry https://registry.npmmirror.com` |
