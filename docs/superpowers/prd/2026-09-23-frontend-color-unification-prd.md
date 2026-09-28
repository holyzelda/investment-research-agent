# 朱雀投研智能体前端页面颜色统一 PRD

- 日期：2026-09-23
- 状态：待评审
- 关联文档：
  - 审计清单（逐文件明细）：`docs/superpowers/specs/2026-09-23-frontend-color-unification-audit.md`
  - 设计规格：`docs/superpowers/specs/2026-09-23-frontend-color-unification-design.md`

## 1. 背景与问题

- 前端 UI 颜色**硬编码散布**在业务代码中：审计基线 `4faa051` 下共 **33 个文件 / 224 行** 直接写死 `#hex`、`rgb()/rgba()`（明细见审计文档），且多个页面重复定义同义色（如登录页本地 `--cyan/--blue`、policy-market 本地 `--pm-*`），彼此不一致。
- 项目采用玄策（XC）设计体系，`src/design-system/tokens.css` 已定义 241 个 `--xc-*` token（含深色基线 + `data-theme="light"` 亮色覆盖），但业务代码未统一消费，导致：
  - **深浅主题切换失灵**：硬编码色不随主题变化，亮色主题下部分区域仍是暗色硬编码；
  - **维护成本高**：改一个品牌色需改多处且容易漏；
  - **视觉不统一**：同义色各页面深浅不一。

## 2. 目标与非目标

### 2.1 目标
- 所有业务页面 UI 颜色统一由 `--xc-*` token 提供，业务代码不再内联 hex / rgb() / rgba() 字面量；
- 深浅主题下语义自动跟随；
- 页面专属强调色固化为命名 token，跨页面同义色共用同一 token，消灭重复定义（`--pm-*`、login 本地色等）；
- 图表/Canvas 运行时颜色通过 `xcVar()` / `xcRgba()` 读取 token，保证主题联动。

### 2.2 非目标
- 不改动信息架构、交互与布局；
- 不重构视觉风格（色值语义与原设计一致，仅改来源）；
- 不动位图素材（Logo、报告封面底图等）。

## 3. 现状审计摘要

- 基线：`4faa051`；范围：`agent-frontend/src`；排除 `tokens.css`（定义源）。
- 系统级色源唯一：`tokens.css` 241 个 `--xc-*` token。
- 业务硬编码：**33 个文件 / 224 行**。Top 文件：`login.vue`（55）、`WelcomeScene.vue`（53）、`ProvinceIndexDetail.vue`（24）、`TrialQuotaBadge.vue`（11）、`ResultCard.vue`（7）、`TieLineFilterBar.vue`（6）等。
- 细节：逐文件行号与色值见 `2026-09-23-frontend-color-unification-audit.md`。

## 4. 方案设计概要

### 4.1 token 消费规则
- 颜色一律 `var(--xc-*)`；透明度一律 `color-mix(in srgb, var(--xc-*) pct%, transparent)`；
- 涨跌语义 `--xc-trade-up/down` 与状态语义 `--xc-status-*` 两套不混用；
- 图表演示（ECharts option / Canvas）用运行时 `xcVar(token)` / `xcRgba(token, alpha)`，随主题重渲染。

### 4.2 新增基建
- `design-system/tokens.css`：补充缺失语义 token（`--xc-surface-deep`、`--xc-report-*`、`--xc-text-*` 等，已含亮色覆盖）；
- 运行时工具：`xcVar()`（读取 CSS 变量）与 `xcRgba()`（token + 透明度合成）。

### 4.3 豁免清单
- `tokens.css` 本身（定义源）；
- `WelcomeScene.vue` 的 `--scene-*` SVG 粒子/动画色（纯视觉，可等价替换时顺手替换）；
- `src/assets/` 位图素材；
- `layout/index.vue` mask-image 的 `#000`（遮罩透明度运算色，非展示色）。

## 5. 实施范围与批次计划

| 批次 | 范围 | 交付物 |
| --- | --- | --- |
| 1 | 文档 | 规格 + 审计清单 |
| 2 | 基建 | tokens.css 扩充 + `xcRgba()` |
| 3 | 登录 | `views/login.vue` |
| 4 | 指数地图 | `views/index-map/**`（7 文件） |
| 5 | 联络线 | `views/tie-line/**` + `tieLineMapOption.js` + 测试同步 |
| 6 | 政策市场 | `views/policy-market/**`（6 文件，含 `--pm-*` 收敛） |
| 7 | 公共组件/home | `src/components/**` + `views/home/components/**` |
| 8 | 台账/结果/分享 | `calculation-ledger`、`calculation-result`、`calculation-share` |
| 9 | 样式收尾 | `report-print.css` 水印 + `layout/index.vue` 背板渐层 + 测试同步 |
| 10 | 验收 | 全仓复查清零（仅豁免项剩余） |

## 6. 验收标准

- 全仓扫描 `agent-frontend/src`（排除豁免）：无 `#hex`、`rgb()/rgba()`、`hsl()/hsla()` 残留；
- 深/亮两种主题下关键页面（登录、首页、报告、台账）视觉语义正确；
- 测试：`npm test` 全量通过（含同步更新的颜色断言），`npm run build` 通过；
- 每批次独立 commit，可单独回滚。

## 7. 风险与注意

- 亮色主题下蓝底按钮白字（`--xc-text-strong` 亮色变深）对比度需走查；
- 测试对旧色值字面量的断言需随源码同步更新，以源码为准；
- `layout/index.vue` 背板渐层透明度用 `color-mix` 收敛后需回归欢迎语对比度。

## 8. 交付与协作流程

- 流程：规格文档 → 分批次实现 → 每批 `npm test` + `npm run build` → 独立 commit → 推送 → MR 合入 `dev`；
- 硬性约定：未经用户明确要求不执行 `git add/commit/push`（见仓库根 `CLAUDE.md`）；文档与源码冲突时以源码和测试为准。

## 9. 执行任务清单（截图确认项）

> 本节为用户根据页面截图确认的待执行任务。执行前需先获得用户明确的“执行 P01”指令；仅更新本节不代表已修改源码。
>
> 本条只统一外层大卡片背景；不改变页面布局、尺寸、边框、阴影、文字颜色、图表颜色及右侧详情卡片内部的小卡片背景。

### P01｜朱雀寻龙图外层卡片背景统一

- 执行状态：已完成
- 执行日期：2026-09-23
- 验证结果：指数地图相关测试 5 个文件、16 条用例全部通过；`npm run build` 通过

**页面：** `agent-frontend/src/views/index-map/index.vue` 对应“全国储能投资指数 / 朱雀寻龙图”页面。

**统一目标：** 以下 4 类左侧卡片和 1 个右侧详情大卡片，统一使用左侧应用侧边栏的灰色大背景：

```css
background: var(--xc-surface-raised);
```

暗色主题下对应的现有 token 为：

```css
--xc-surface-raised: rgba(44, 46, 55, 0.92);
```

#### P01-1｜左侧地图大卡片

- 文件：`agent-frontend/src/views/index-map/index.vue`
- 选择器：`.index-map-page__map`
- 位置：约第 57 行
- 当前背景：`rgba(20, 27, 31, 0.96)`
- 目标背景：`var(--xc-surface-raised)`

#### P01-2｜左侧“全国均值”汇总卡片

- 文件：`agent-frontend/src/views/index-map/components/IndexSummaryCards.vue`
- 选择器：`.index-summary-cards`
- 位置：约第 14 行
- 当前背景：`rgba(40, 48, 52, 0.72)`
- 目标背景：`var(--xc-surface-raised)`

#### P01-3｜左侧“投资热力榜”卡片

- 文件：`agent-frontend/src/views/index-map/index.vue`
- 选择器：`.index-map-page__rankings`
- 位置：约第 60 行
- 当前背景：`rgba(40, 48, 52, 0.72)`
- 目标背景：`var(--xc-surface-raised)`
- 说明：该容器同时承载“投资热力榜”和“收益稳定榜”，两张榜单外层统一处理。

#### P01-4｜左侧“收益稳定榜”卡片

- 文件：`agent-frontend/src/views/index-map/index.vue`
- 选择器：`.index-map-page__rankings`
- 位置：约第 60 行
- 当前背景：`rgba(40, 48, 52, 0.72)`
- 目标背景：`var(--xc-surface-raised)`
- 说明：与 P01-3 共用同一个外层容器；不单独改变两张榜单内部行项目的背景和选中状态背景。

#### P01-5｜右侧“蒙西”详情大卡片

- 文件：`agent-frontend/src/views/index-map/components/ProvinceIndexDetail.vue`
- 选择器：`.province-detail`
- 位置：约第 83 行
- 当前背景：`#222a2e`
- 目标背景：`var(--xc-surface-raised)`

### P01 明确不修改范围

右侧“蒙西”详情大卡片内部的小卡片背景保持原样，包括：

- `.province-detail__score` 分数卡片及其渐变背景；
- `.province-detail__grid article` 市场化成熟度小卡片；
- `.province-detail__capacity` 新能源、火电、储能装机结构小卡片；
- `.province-detail__analysis` 分析说明卡片；
- 评分环内部背景 `.province-detail__grade-ring > div`；
- 内部进度条、边框、状态色和强调色。

同时保持以下样式不变：

- 地图内容和地图工具栏；地图左下角图例背景另由 P03 统一；
- 全国均值、两张榜单的内部文字、分隔线和选中行背景；
- 页面布局、卡片尺寸、圆角、边框、阴影和间距。

### P01 验收标准

- 5 个指定外层卡片的 `background` 均为 `var(--xc-surface-raised)`；
- 右侧详情内部小卡片的背景声明不发生变化；
- 深色主题下与左侧应用侧边栏灰色大背景视觉一致；
- 亮色主题下自动跟随 `--xc-surface-raised` 的主题覆盖；
- 执行时只修改上述 3 个文件；
- 执行后运行指数地图相关测试和 `npm run build`；
- 默认不执行 `git add`、`git commit`、`git push`。

### P02｜朱雀寻龙图榜单选中态统一

- 执行状态：已完成
- 执行日期：2026-09-23
- 页面：朱雀寻龙图底部“投资热力榜”和“收益稳定榜”
- 文件：`agent-frontend/src/views/index-map/components/IndexRankingList.vue`

#### 需求

- 用户选择某个省份后，对应榜单行的背景色与“朱雀星核”左侧菜单高亮背景一致；
- 继续保留选中行左侧的蓝色竖线；
- 不改变普通行背景、文字颜色、榜单布局和点击逻辑；鼠标悬停行的背景同步使用同一高亮 token。

#### 实现

- 侧栏菜单高亮来源：`.ir-shell__nav-item.is-active`；
- 统一背景 token：`var(--xc-surface-control)`；
- 榜单悬停行：`button:hover { background: var(--xc-surface-control); }`；
- 榜单选中行：`button.is-active { background: var(--xc-surface-control); }`；
- 蓝色竖线保持：`button.is-active::before { background: var(--xc-accent-blue); }`；
- 悬停态与选中态背景保持一致，避免悬停省份与当前选中省份出现不同灰色。

#### 验收标准

- “投资热力榜”和“收益稳定榜”中当前选中省份均使用 `var(--xc-surface-control)`；
- 两张榜单中鼠标悬停省份均使用 `var(--xc-surface-control)`，与右侧卡片背景视觉一致；
- 选中行左侧蓝色竖线仍清晰显示；
- 两张榜单选择同一省份时，选中态保持同步；
- 指数地图相关测试和前端构建通过；
- 仅本地提交，不推送远程分支。

### P04｜联络线地图背景及控件交互色统一

- 执行状态：已完成
- 执行日期：2026-09-23
- 页面：跨省跨区联络线
- 文件：
  - `agent-frontend/src/views/tie-line/index.vue`
  - `agent-frontend/src/views/tie-line/components/TieLineFilterBar.vue`
  - `agent-frontend/src/views/tie-line/components/TieLinePowerTrend.vue`
  - `agent-frontend/tests/tie-line-layout.spec.js`
  - `agent-frontend/tests/tie-line-filter-bar.spec.js`
  - `agent-frontend/tests/tie-line-power-trend.spec.js`

#### 需求

- 联络线地图板块整体大背景与左侧应用侧边栏灰色大背景一致；
- 顶部“起点”“终点”“额定容量”控件，以及右侧功率趋势日期快捷按钮，悬停时显示蓝色边框，效果参照朱雀星核示例项目按钮；
- 上述控件有已选状态时显示蓝色背景，效果参照朱雀星核上传电价文件按钮的蓝色选中反馈；
- 不改动地图内容、筛选行为、功率趋势数据或布局。

#### 实现

- 联络线页面背景及右侧遮罩渐变终点使用 `var(--xc-surface-raised)`，与侧边栏 `.ir-shell` 背景一致；
- 筛选控件悬停边框使用 `var(--xc-border-accent)`，已选状态背景使用 `var(--xc-accent-blue-soft)`；
- 功率趋势日期按钮悬停边框使用 `var(--xc-border-accent)`，当前选中日期使用 `var(--xc-accent-blue-soft)` 背景及蓝色边框。

#### 验收标准

- 联络线地图板块主要背景与左侧侧边栏使用同一 `--xc-surface-raised` token；
- 三个筛选控件和日期按钮悬停均显示蓝色边框；
- 已选起点/终点/容量和当前日期范围显示蓝色底色；
- 联络线相关测试及前端构建通过；
- 默认仅修改本地文件，不执行远程操作或 Git 提交。
- 验证结果：联络线相关测试 10 个文件、73 条用例全部通过；`npm run build` 通过；`git diff --check` 通过。

### P03｜朱雀寻龙图地图图例与装机结构卡片背景统一

- 执行状态：已完成
- 执行日期：2026-09-23
- 页面：朱雀寻龙图地图左下角图例，以及右侧“装机结构 · 在运”板块中的新能源、火电、储能卡片
- 文件：
  - `agent-frontend/src/views/index-map/components/ChinaIndexMap.vue`
  - `agent-frontend/src/views/index-map/components/ProvinceIndexDetail.vue`（仅作视觉基准，未修改）
  - `agent-frontend/tests/index-map-color.spec.js`

#### 需求

- 地图左下角图例卡片背景与右侧装机结构小卡片背景保持一致；
- 用户截图中“储能”卡片作为右侧装机结构卡片的示例基准；
- 不改变图例色块、文字、边框、圆角、布局和地图交互；不改变右侧装机结构卡片的既有样式。

#### 实现

- 地图图例 `.china-index-map__legend` 背景统一为 `rgba(255, 255, 255, 0.018)`；
- 右侧 `.province-detail__capacity` 当前背景已是 `rgba(255, 255, 255, 0.018)`，本批次保持不变；
- 增加源码断言，防止两处背景值后续出现不一致。

#### 验收标准

- 地图左下角图例与右侧“装机结构 · 在运”卡片背景声明完全一致；
- “储能”卡片及同板块其他卡片的布局、标记色和内容不变；
- 指数地图相关测试和前端构建通过；
- 仅本地提交，不执行远程拉取、合并或推送。

### P05｜专业数据速查页面强调色与卡片背景统一

- 执行状态：代码已修改，待验证
- 执行日期：2026-09-23
- 页面：专业数据速查（政策研判工作台）
- 参考：图 1 的专业数据速查页面；图 2 中朱雀星核上传电价文件文字的蓝色；左侧整个侧边栏灰色大背景
- 文件：
  - `agent-frontend/src/views/policy-market/index.vue`
  - `agent-frontend/src/views/policy-market/components/ConsultationComposer.vue`
  - `agent-frontend/src/views/policy-market/components/MarketPulse.vue`
  - `agent-frontend/tests/policy-market-page.spec.js`

#### 需求

- 专业数据速查页面中原有青色文字、图标、边框和强调色统一改为与上传电价文件文字一致的蓝色；使用 `var(--xc-accent-blue)`，不改变原为白色或灰色的普通文字；
- “研究问题”卡片和右侧“资讯概览”卡片背景改为与左侧整个侧边栏灰色大背景一致，使用 `var(--xc-surface-raised)`；
- 保持布局、内容、交互、非青色颜色和其他卡片背景不变。

#### 实现

- 页面强调色 `--pm-accent` 改为 `var(--xc-accent-blue)`，覆盖该页面共享强调色的文字、图标和交互边框；
- 页面卡片背景变量 `--pm-surface` 改为 `var(--xc-surface-raised)`，供“研究问题”和“资讯概览”卡片共用；
- 日期范围选中区域的青色透明底改为基于蓝色 token 的 `color-mix()`。

#### 验收标准

- 原青色的页面强调文字、图标、边框和选中强调显示为 XC 蓝色 token；
- “研究问题”与“资讯概览”卡片均使用 `var(--xc-surface-raised)`，与侧栏大背景一致；
- 原白色/灰色普通文字、其他卡片背景、页面布局及业务交互不变；
- 专业数据速查页面相关测试和前端构建通过；
- 仅修改本地文件，不执行 Git 提交或远程操作。


### P06｜朱雀寻龙图卡片字体与显示样式参照 ZRA-3 统一

- 执行状态：已完成
- 执行日期：2026-09-24
- 页面：朱雀寻龙图
- 参考页面：`D:\workbench\朱雀投研智能体\页面颜色统一\朱雀投研智能体 ZRA-3.html`
- 修改文件：
  - `agent-frontend/src/views/index-map/components/IndexSummaryCards.vue`
  - `agent-frontend/src/views/index-map/components/IndexRankingList.vue`
  - `agent-frontend/src/views/index-map/components/ProvinceIndexDetail.vue`
  - `agent-frontend/tests/index-summary-cards.spec.js`
  - `agent-frontend/tests/index-ranking-list.spec.js`
  - `agent-frontend/tests/index-map-detail.spec.js`
  - `agent-frontend/tests/index-map-color.spec.js`

#### 需求

- 参照 ZRA-3 页面左侧地图下方卡片和右侧省份详情卡片，统一朱雀寻龙图的标题、辅助文字、数字、单位、排名、指标、因子分析和装机结构的字号、字重、圆角、内边距、间距及进度条显示样式。
- 覆盖左侧“全国均值汇总”“投资热力榜”“收益稳定榜”，以及右侧省份详情、内部指数、归因指标、因子分析、装机结构等已有卡片。
- 仅调整已有页面的显示样式；不新增数据、不修改接口、不修改字段、不调整排序，不改变地图和既有业务逻辑。

#### 明确保持不变

- 保持所有卡片背景颜色、边框颜色语义、鼠标悬停颜色、选中颜色和蓝色竖线不变。
- 保持地图内容、地图交互、省份选择、榜单选择和右侧数据展示不变。
- 不修改模板数据绑定和脚本逻辑，不执行 Git 提交、远程拉取或推送。

#### 实现记录

- 汇总卡片调整为更接近 ZRA-3 的 16px 圆角、14px/18px 内边距及更清晰的标题与数值层级，保留原 `var(--xc-surface-raised)` 背景。
- 榜单调整行间距、内边距、排名尺寸、省份名称和数值字号，保留现有 `var(--xc-surface-control)` 悬停/选中背景及 `var(--xc-accent-blue)` 蓝色竖线。
- 右侧详情调整外层及指标/装机结构子卡片圆角、内边距、章节间距、指标数字、因子条和装机结构文字层级，保留原卡片背景、边框和状态色。
- 增加源码样式断言，覆盖尺寸调整和背景/交互样式不变约束。

#### 验收标准

- 左侧三个区域及右侧详情卡片的字体层级、数字突出度、圆角、间距和进度条尺寸与 ZRA-3 参考风格一致。
- 卡片背景、边框、悬停态、选中态和蓝色竖线与本次修改前保持一致。
- 页面中的接口数据、数据字段、数据内容、排序及交互行为完全不变。
- 朱雀寻龙图相关测试通过，`git diff --check` 通过，前端构建通过。
- 验证结果：朱雀寻龙图定向测试 4 个文件、15 条用例全部通过；`npm run build` 通过；`git diff --check` 通过；未执行 Git 提交、远程拉取或推送。

### P07｜朱雀寻龙图汇总卡片、榜单和省份详情细节优化

- 执行状态：已完成
- 执行日期：2026-09-24
- 页面：朱雀寻龙图
- 参考页面：`D:\workbench\朱雀投研智能体\页面颜色统一\朱雀投研智能体 ZRA-3.html`
- 修改文件：
  - `agent-frontend/src/views/index-map/components/IndexSummaryCards.vue`
  - `agent-frontend/src/views/index-map/components/IndexRankingList.vue`
  - `agent-frontend/src/views/index-map/components/ProvinceIndexDetail.vue`
  - `agent-frontend/tests/index-summary-cards.spec.js`
  - `agent-frontend/tests/index-ranking-list.spec.js`
  - `agent-frontend/tests/index-map-detail.spec.js`
  - `agent-frontend/tests/index-map-color.spec.js`

#### 需求

- 将“全国均值”“领跑省份”“已开通区域”“高潜待挖掘”从一个连体区域调整为四张独立小卡片，每张卡片左侧增加参考 ZRA-3 的渐变色竖线，并在保证信息清晰的前提下适当压缩卡片高度。
- 在“投资热力榜”和“收益稳定榜”标题前增加参考 ZRA-3 的对应图标；排名序号改为小号方形徽章，前三名使用不同强调色。
- 右侧省份详情整体字体提高一个字号；“归因分析 · 市场化成熟度”辅助说明和“归因分析 · 因子贡献度”因子标签改为白色文字。
- 在“装机结构 · 在运”标题下增加按现有装机占比数据绘制的合计 GW 长条统计；标题右上角合计数值的字号和数字样式与下方装机卡片容量数值一致。

#### 明确保持不变

- 保持接口、字段、数据内容、数据排序和业务逻辑不变，不新增或改写业务数据。
- 保持地图内容、地图交互、省份选择和榜单点击行为不变。
- 保持卡片背景颜色、榜单悬停背景、选中背景及选中行蓝色竖线不变。
- 默认不执行 `git add`、`git commit`、`git pull` 或 `git push`。

#### 实现记录

- 四个汇总项改为带独立边框、圆角、背景和渐变左竖线的小卡片，外层仅负责四列布局与间距。
- 榜单标题使用火焰和盾牌图标区分热力榜与稳定榜；排名前三位使用金色、蓝色和紫色方形徽章，其他排名保持低强调样式。
- 省份详情在既有布局内统一提升文字字号，将指定辅助文字改为强文字色，并新增复用新能源、火电、储能现有标记色的装机占比长条。
- 装机合计标题拆分为说明、数值和单位，合计数值复用装机容量数字的字号与数字字体。

#### 验收标准

- 四个汇总项是相互独立的卡片，均有左侧渐变竖线，卡片高度适中且原数据完整显示。
- 两个榜单标题图标正确，前三名序号徽章可区分，同时原悬停态、选中态和蓝色竖线保持不变。
- 右侧详情文字层级更清晰，指定说明文字显示为白色；装机结构显示合计占比长条，合计数字与装机容量数字字号一致。
- 朱雀寻龙图定向测试、`npm run build` 和 `git diff --check` 通过。
- 验证结果：朱雀寻龙图定向测试 4 个文件、16 条用例全部通过；`npm run build` 通过；`git diff --check` 通过；未执行 Git 提交、远程拉取或推送。

### P08｜朱雀寻龙图页面纵向比例优化

- 执行状态：已完成
- 执行日期：2026-09-24
- 页面：朱雀寻龙图
- 修改文件：
  - `agent-frontend/src/views/index-map/index.vue`
  - `agent-frontend/src/views/index-map/components/IndexSummaryCards.vue`
  - `agent-frontend/src/views/index-map/components/IndexRankingList.vue`
  - `agent-frontend/tests/index-map-layout.spec.js`
  - `agent-frontend/tests/index-summary-cards.spec.js`
  - `agent-frontend/tests/index-ranking-list.spec.js`

#### 需求

- 增加页面顶部地图卡片的可用高度，使地图区域在当前页面中更舒展。
- 适当压缩地图下方四张汇总卡片的高度，为地图释放纵向空间。
- 适当压缩“投资热力榜”和“收益稳定榜”的整体高度，但保留标题图标、排名徽章、数据内容和可读性。

#### 明确保持不变

- 不修改地图内容、地图缩放与点击交互，不修改接口、字段、数据和排序。
- 不修改卡片背景、文字颜色、榜单悬停态、选中态和蓝色竖线。
- 不缩小汇总卡片核心数值、榜单标题、省份名称和分值的字号。
- 默认不执行 `git add`、`git commit`、`git pull` 或 `git push`。

#### 实现记录

- 左侧主区域地图行最小高度由 300px 提高到 340px，剩余高度仍由 CSS Grid 自适应分配。
- 四张汇总卡片最小高度由 68px 调整为 60px，并减少上下内边距与渐变竖线的上下留白。
- 两张榜单减少外层与标题上下留白，榜单行最小高度由 36px 调整为 32px，在保持原字号的同时降低整体高度。

#### 验收标准

- 常规桌面尺寸下，顶部地图区域明显高于修改前，地图主体显示更舒展。
- 四张汇总卡片及两个榜单区域高度适当缩小，信息不重叠、不截断。
- 原有颜色、字体层级、渐变竖线、排名徽章、悬停和选中交互保持不变。
- 朱雀寻龙图定向测试、`npm run build` 和 `git diff --check` 通过。
- 验证结果：朱雀寻龙图定向测试 5 个文件、17 条用例全部通过；`npm run build` 通过；`git diff --check` 通过；未执行 Git 提交、远程拉取或推送。

### P10｜联络线地图右侧详情卡片化布局优化

- 执行状态：已完成
- 执行日期：2026-09-24
- 页面：联络线地图
- 修改文件：
  - `agent-frontend/src/views/tie-line/index.vue`
  - `agent-frontend/src/views/tie-line/components/TieLineDetailPanel.vue`
  - `agent-frontend/src/views/tie-line/components/TieLinePowerTrend.vue`
  - `agent-frontend/src/views/tie-line/components/TieLineStatsBar.vue`
  - `agent-frontend/tests/tie-line-layout.spec.js`
  - `agent-frontend/tests/tie-line-power-trend.spec.js`

#### 需求

- 将右侧“线路档案、线路名称、线路类型”放入一个独立详情卡片。
- 将“额定容量、 电压等级、线路长度、投运年份”放入一个独立指标卡片。
- 将线路名称字号提高到 24px–26px；起点和终点改为两个独立节点卡片，中间使用明显的方向箭头或连接线。
- 提高起点、终点名称字号，将地区名称放在下一行作为辅助信息，并使用高亮色突出起点、终点名称。
- 将功率趋势区域扩展到右侧下方可用空白空间，提高图表可读性。
- 右侧详情区域与顶部联络线统计栏使用一致的宽度和右边界。

#### 明确保持不变

- 保持接口、字段、数据内容、排序、地图内容、筛选逻辑和线路选择逻辑不变。
- 保持功率趋势日期范围切换、自定义日期、加载态、错误态和空数据态行为不变。
- 不新增模拟数据，不修改额定容量、线路名称、起点、终点及统计值。
- 默认不执行 `git push`；本次仅在用户明确要求时执行本地提交。

#### 验收标准

- 右侧至少清晰呈现线路概览卡片、线路指标卡片和功率趋势卡片。
- “吉泉直流”名称字号达到 24px–26px，起点和终点节点可明确识别，方向箭头清晰可见。
- 四项线路指标在同一张卡片内以两列布局呈现，数据完整且不截断。
- 功率趋势图利用右侧下方空间增大显示区域，日期按钮和图表交互不受影响。
- 右侧详情卡片与顶部统计栏宽度及右边界对齐。
- 联络线定向测试、`npm run build` 和 `git diff --check` 通过。
- 验证结果：联络线定向测试 6 个文件、40 条用例全部通过；`npm run build` 通过；`git diff --check` 通过；未执行 Git 提交、远程拉取或推送。

#### P10 返修记录｜按确认截图回退视觉表现

- 昌吉换流站、古泉换流站恢复为普通白色文字，移除两个节点卡片，仅保留节点圆点、地区辅助文字和居中的方向箭头。
- 四项线路指标继续置于一个整体卡片内，移除四个指标的小卡片背景、边框和圆角，改为两行两列并使用行分隔线。
- 功率趋势移除外层卡片，图表固定为适度增高的 280px，保留并显式显示横坐标，减少底部空白。
- 保持右侧详情与顶部统计栏共用 `--tl-detail-width`，接口、数据、地图和交互逻辑不变。
- 箭头位置修正：将连接线与箭头作为一个整体连接组置于起点和终点之间的中央区域，箭头保留在连接组末端，不再单独定位在线段中点。
- 返修验收：联络线定向测试 6 个文件、40 条用例全部通过；`npm run build` 通过；`git diff --check` 通过；未执行 Git 提交、远程拉取或推送。

#### P10 返修记录｜连接组按站名对齐并居中

- 确认日期：2026-09-28。
- 连接线与箭头仅和起点、终点的第一行站名垂直对齐，不再按照“站名＋地区”两行内容的整体高度居中。
- 起点列和终点列按各自内容宽度布局，中间区域自动占据剩余空间；连接线与箭头作为固定宽度整体在该区域水平居中，避免靠近古泉换流站。
- 地区辅助信息、节点圆点、站名颜色、线路数据以及其他 P10 布局保持不变。

#### P10 返修记录｜恢复紧凑的起终点间距

- 确认日期：2026-09-28。
- 起点与终点之间不再使用占满剩余空间的弹性连接区域，恢复为固定宽度的紧凑连接区域。
- 连接线与箭头继续与第一行站名对齐，并作为整体在起点和终点之间居中。
- 地区辅助信息、节点圆点、站名颜色、线路数据及其他 P10 布局保持不变。

#### P10 返修记录｜恢复上一版连接区域布局

- 确认日期：2026-09-28。
- 按确认要求恢复上一版连接区域：起点和终点按内容宽度布局，中间连接区域占据两者之间的可用空间。
- 连接线与箭头整体保持水平居中，并继续与第一行站名对齐；连接组宽度恢复为 `64px`。
- 地区辅助信息、节点圆点、站名颜色、线路数据及其他 P10 布局保持不变。

### P09｜朱雀寻龙图汇总卡片移除左侧竖线

- 执行状态：已完成
- 执行日期：2026-09-24
- 页面：朱雀寻龙图
- 修改文件：
  - `agent-frontend/src/views/index-map/components/IndexSummaryCards.vue`
  - `agent-frontend/tests/index-summary-cards.spec.js`
  - `agent-frontend/tests/index-map-layout.spec.js`

#### 需求

- 移除“全国均值”“领跑省份”“已开通区域”“高潜待挖掘”四张汇总卡片左侧的渐变色竖线。

#### 明确保持不变

- 保持四张卡片的独立布局、尺寸、背景色、边框、圆角、文字样式、数据和页面交互不变。
- 不修改地图内容、接口、字段、业务逻辑及其他页面样式。
- 默认不执行 `git add`、`git commit`、`git pull` 或 `git push`。

#### 实现记录

- 删除汇总卡片的 `::before` 伪元素及四组渐变色样式。
- 将卡片左侧内边距恢复为与右侧一致的 `14px`，避免移除竖线后产生多余空白。

#### 验收标准

- 四张汇总卡片左侧均不再显示渐变色竖线。
- 卡片背景、边框、圆角、字号、数据和高度保持原样，内容不截断、不重叠。
- 汇总卡片定向测试、`npm run build` 和 `git diff --check` 通过。
- 验证结果：朱雀寻龙图定向测试 5 个文件、17 条用例全部通过；`npm run build` 通过；`git diff --check` 通过；未执行 Git 提交、远程拉取或推送。
