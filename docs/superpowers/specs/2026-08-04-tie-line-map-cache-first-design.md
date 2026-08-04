# 联络线地图缓存优先加载优化设计

## 背景

联络线地图页面每次打开都会调用 `store.loadLines()` 重新请求 `/ir/tie-lines`，并在请求期间显示整屏加载态。即使 Pinia store 中已经保留了上一次加载成功的联络线基础数据，页面再次进入时仍会等待接口返回后才展示地图，造成“每次打开都要加载好一会”的体感。

联络线基础资料的实时性要求较低，本次优化采用“缓存优先 + 静默刷新”的低风险方案：首次打开正常加载；同一登录会话内再次打开时立即展示已有数据，同时后台刷新。

## 目标

1. 首次进入联络线地图页面时，保持现有加载、错误和重试体验。
2. 同一前端会话内再次进入页面时，如果已有成功加载的数据，立即展示地图，不显示整屏加载遮罩。
3. 再次进入页面时后台静默刷新联络线基础数据，刷新成功后更新线路、统计和筛选项。
4. 静默刷新失败时保留旧数据，不打断用户浏览。
5. 不改动详情接口和功率趋势接口的实时加载逻辑。

## 非目标

1. 不做路由级预加载。
2. 不拆分 ECharts 地图渲染层级。
3. 不引入本地持久化缓存，例如 `localStorage` 或 IndexedDB。
4. 不修改后端接口契约。

## 状态设计

在 `agent-frontend/src/store/modules/tieLine.js` 的 Pinia state 中增加：

- `loaded`：是否至少成功加载过一次联络线基础数据。
- `refreshing`：是否正在静默刷新。
- `lastLoadedAt`：最后一次成功加载时间戳，仅用于调试和未来扩展 TTL，本次不基于它做过期判断。

`loading` 继续表示首次或强制加载时的阻塞加载态。`refreshing` 表示已有缓存时的后台刷新态，两者不混用。

## 数据加载设计

将 `loadLines` 改为接收可选参数：

```js
async loadLines({ force = false, silent = false } = {})
```

行为如下：

1. 如果已有 `loaded === true` 且 `force === false` 且不是显式静默刷新，调用方可直接返回缓存，避免无意义重复请求。
2. 首次加载或强制加载时：
   - 设置 `loading = true`。
   - 清空 `error`。
   - 请求成功后写入 `lines`、`stats`、`filters`，设置 `loaded = true` 和 `lastLoadedAt`。
   - 请求失败时，如果没有已加载数据，则清空 `lines` 并展示错误；如果已有数据，则保留旧数据。
3. 静默刷新时：
   - 设置 `refreshing = true`，不设置 `loading`。
   - 不清空 `lines`、`stats`、`filters`。
   - 请求成功后替换基础数据。
   - 请求失败时保留旧数据，不显示整屏错误。

为避免旧异步响应覆盖新状态，保留现有异步保护风格，可在 store 内增加 `lineRequestVersion`。后发请求的版本号大于先发请求时，先发请求返回后不再写入状态。

## 页面设计

在 `agent-frontend/src/views/tie-line/index.vue` 中调整挂载逻辑：

- 页面 `onMounted` 调用缓存优先入口：
  - 如果 `store.loaded` 为 false：执行 `store.loadLines()`，保持阻塞 loading。
  - 如果 `store.loaded` 为 true：立即展示现有 `store.visibleLines`，并执行 `store.loadLines({ force: true, silent: true })` 静默刷新。
- 整屏加载态条件从 `store.loading` 改为 `store.loading && !store.loaded`。
- 错误态只在 `store.error && !store.loaded` 时阻塞展示。
- 重试按钮使用 `store.loadLines({ force: true })`，适合首次失败或用户主动要求重新加载。

静默刷新期间不新增明显视觉提示，避免干扰地图使用。后续如有需要，可在统计栏或工具栏增加轻量“正在更新”状态。

## 地图设计

`ChinaTieLineMap.vue` 本次不做结构性改造：

- 缓存命中时，组件直接接收 store 中已有 `visibleLines` 并初始化地图。
- 静默刷新成功后，现有 watcher 根据新的 `lines` 替换业务 `series`。
- watcher 仍保留现有视角保护逻辑，避免刷新时重置用户已缩放或拖拽的地图视角。

## 错误处理

1. 首次加载失败：维持现有“数据加载失败 + 重试”页面。
2. 静默刷新失败：保留旧地图数据，不清空列表，不显示阻塞错误页。
3. 强制刷新失败且已有缓存：保留旧数据，同时设置可读错误信息，后续可由页面选择是否展示非阻塞提示。
4. 筛选和选中逻辑沿用现有 `_dropSelectionIfHidden`，刷新后如果已选线路不再存在，应清空详情，避免地图与右侧详情不一致。

## 测试设计

更新或新增前端 Vitest 用例：

1. `tie-line-store.spec.js`
   - 首次 `loadLines()` 成功后写入 `lines`、`stats`、`filters`，并设置 `loaded = true`。
   - 静默刷新时不清空旧 `lines`，不进入阻塞 `loading`。
   - 静默刷新失败时保留旧数据。
   - 无缓存加载失败时清空数据并设置错误信息。
   - 后发请求完成后，先发请求不得覆盖状态。
2. 页面测试
   - 没有缓存且加载中时显示加载态。
   - 已有缓存且静默刷新时展示地图，不显示整屏加载态。
   - 重试按钮触发强制加载。

## 验收标准

1. 第一次打开联络线地图页面仍可正常加载并展示数据。
2. 同一前端会话内离开再返回联络线地图页面时，地图立即展示已有数据。
3. 再次进入页面会后台刷新 `/ir/tie-lines`，刷新失败不会清空已展示地图。
4. 现有筛选、详情、功率趋势、地图选择和缩放行为不被破坏。
5. 相关 Vitest 测试通过。
