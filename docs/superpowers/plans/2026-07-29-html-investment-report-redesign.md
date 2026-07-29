# AI 储能投资测算报告 HTML 专业化改造计划

## Context

当前正式报告虽已有固定七章、表格、六类 ECharts 图表和 AI 分析，但整体仍是窄版、同节奏的深色长页，封面留白失衡，表格偏 Excel，图表说明和 AI 结论层级不足；现有示例 PDF 还是单张长图，缺少真正 A4 分页、可搜索文本、动态页眉页脚与专业打印体验。本次第一阶段只升级报告产品框架和展示能力，不改变业务逻辑、字段、七章内容、数据契约、图表类型、计算规则、警戒线或语义色；第二阶段再逐表、逐图精修。

目标风格为“专业 + 科技 + 咨询”：采用已确认的储能主题竖版素材作为封面，正文延续克制的三层深色体系；网页保持连续宽版 HTML 阅读，导出通过 Paged.js 生成真正的 A4 多页报告并先展示分页预览。

## 1. 建立报告专用视觉 token 与封面资产

- 将 `D:\0_工作\2026\投研智能体\原型设计\报告结果设计\报告首页素材.png` 复制到 `agent-frontend/src/assets/report/`，由 Vite 受管引用，不保留工作盘绝对路径。
- 在 `src/design-system/tokens.css` 增加报告域 token：
  - 从素材底部中心及左右区域取样确定正文背景，并与现有 XC 深色表面协调；
  - 页面、卡片、嵌套说明区三层深色表面；
  - 深色表头、斑马行、图表网格、低对比边框、AI/说明背景、封面摘要卡和渐隐层；
  - 强调继续复用 XC 品牌蓝，风险/警戒及图表类别继续复用现有语义色。
- Vue 组件和报告 CSS 只使用 `var(--xc-*)`，不新增内联 hex/rgb；字体复用现有中文字体栈，数字复用 `.xc-num`。

## 2. 将报告页面拆成稳定的展示骨架

在 `src/views/report/components/` 新增轻量组件，并重构 `src/views/report/index.vue`：

- `ReportCover.vue`
  - A4 竖版主题素材作为封面主视觉，顶部约 27%、中部 48%、底部 25% 分别承担标题、能源主题、项目摘要；
  - 左上约页面顶部 12% 放 `INVESTMENT ANALYSIS REPORT`、短蓝线及两行中文标题；中文 25–27pt、600、克制咨询型；
  - 底部使用左右约 9% 边距的宽摘要卡：深蓝 72%–78% 不透明、低对比边框、8px 圆角、轻微模糊；项目名通栏，编制单位与日期分栏；标签 9–10pt、值 12–14pt；
  - 不放 Logo；底部渐隐到正文背景。
- `ReportChapter.vue`
  - 统一七个一级章节：Element Plus 线性语义图标、`CHAPTER 01`、现有中文章名和短蓝线；保留“第一章/5.1”等现有编号与内容命名。
  - 一级章节在 Paged.js 正文中强制新页，并通过 `string-set` 提供当前章节页眉内容。
- `ReportSectionHeading.vue`
  - 二级标题 16–18pt/600、卡外唯一标题和短线；三级“如何解读”等使用 12–13pt 文本标签，避免标题条/胶囊式后台感。
- 网页正文宽度严格按当前版心增加约 15%，设置最大宽度和窄屏回落；窄屏不产生页面级横向溢出，宽表只在自身容器横向滚动。
- 全局节奏统一为章节 72px、模块 36px、标题到内容/关联卡片 24px、正文局部 16px；网页和打印均保持宽松节奏（仅表格打印密度单独压缩）。
- 保留 `index.vue` 中现有接口请求、计算属性、字段顺序、格式化函数和缺省文案，避免视觉重构侵入业务逻辑。

## 3. 升级表格体系但不重组业务数据

在 `index.vue` 和报告样式中统一所有表格：

- 深色实表头、白/高对比文字、底部细蓝线；Body 使用非常轻的斑马纹和横向分隔，弱化竖线及完整网格感。
- 文本左对齐；数值、金额、百分比右对齐；单位列按列语义居中或靠近数值；统一 `.xc-num`。
- 仅对 IRR、回收期、ROI 等原本就是最终结论的数值使用品牌蓝和半粗体，不新增 KPI 卡，也不强调普通输入或中间值。
- 屏幕行高约 42–46px、横向 padding 16–18px；打印时仅将表格密度压缩约 10%–15%。
- 第一阶段保持现有字段、列顺序和平面结构；表内业务分组留到第二阶段逐表确认。
- 短表尽量整体不拆；长边界表、政策表、阈值表允许跨页，重复 `thead`，单行尽量不拆。

## 4. 图表逻辑与卡片展示解耦

- 保留 `src/views/report/components/ReportChart.vue` 作为六类 ECharts option 和业务图表逻辑的唯一入口，继续复用 `useEcharts`、`xcVar`、`xcChartColors` 与 `formatNumber`。
- 新增 `ReportChartCard.vue`：
  - 卡外二级标题作为唯一业务标题；卡内承载图表画布、单位/图例辅助信息和“如何解读”浅蓝说明区；
  - 深色克制卡片、低对比边框、8px 圆角、无发光；
  - 图表卡后到 AI 卡 24px。
- 第一阶段允许微调 `grid`、legend、轴字号、symbol、barWidth、画布高度及边距以适应宽版卡片；不得改变 series 数据、图表种类、堆叠、tooltip 精度、偿债分段轴映射、1.0 警戒线、安全余量、敏感性阈值和矩阵判断规则。
- 图表与 PDF 继续使用现有语义色，不改为全蓝或浅色打印。

## 5. 新增报告专用 AI Markdown 卡

- 不修改首页共享的 `src/views/home/components/AiAnswerContent.vue` 默认行为，防止首页对话、生成状态和正式报告之外的 AI 内容意外变成 Markdown。
- 新增：
  - `src/views/report/components/ReportAiAnalysis.vue`
  - `src/views/report/utils/renderReportMarkdown.js`
- 新组件使用独立深色卡片、左侧品牌蓝 Accent、Element Plus 线性智能图标和固定标题“AI 智能分析”；内部 padding 24px，卡后到下一模块 36px；正文最大行宽按约 65–75 个中文字符的视觉宽度校准。
- 新增 `markdown-it` 运行时依赖并同步 `package.json`、`package-lock.json`：
  - `html: false`，禁止原始 HTML；
  - 关闭表格、围栏代码块、块代码、图片等规则；
  - 仅支持标题、段落、加粗、无序/有序列表、引用、行内代码和链接文本；
  - 重写链接 renderer，只输出链接文字，不生成可点击 `<a>`；
  - 按用户确认，仅依赖解析器默认转义，不额外引入 DOMPurify/白名单库；因此配置与测试必须锁定 `html: false`，且禁止把原始 API 文本直接传给 `v-html`，只有受限解析结果可进入报告专用 `v-html`。

## 6. 用 Paged.js 构建真正的 A4 分页导出

新增 `pagedjs` 依赖及报告导出 composable（建议 `src/views/report/composables/usePagedReportExport.js`），替换 `index.vue` 中直接 `window.print()` 的流程：

1. 点击“导出 PDF”后，在当前窗口创建全屏分页预览容器，显示生成状态；不使用 `display:none`、弹窗新窗口或直接改动真实 Vue 报告树。
2. 克隆正式报告为临时静态导出源，将封面与正文拆给两个独立 `Previewer`：
   - 封面命名页无页眉页脚；
   - 正文从新的 Previewer 开始，页码自然从 1 计数，避免跨封面重置计数器的不稳定行为。
3. 正文使用 Paged.js margin boxes：
   - 页眉左：`AI储能投资测算报告`；
   - 页眉右：由一级章名 `string-set` / `string()` 动态更新；
   - 页脚左：编制单位；
   - 页脚右：`第 N 页`。
4. 将封面分页结果与正文分页结果按顺序合并到全屏 A4 预览；用户确认后点击“打印/保存 PDF”，也可关闭返回连续网页。
5. `report-print.css` 负责实际浏览器打印时只显示 Paged.js 输出；新增/拆分 Paged.js 专用样式（如 `report-paged.css`）承载命名页、margin boxes、章节新页、表头重复和语义断页。
6. 保留非常轻量的原生打印兜底，但高级页眉页脚和正文页码以 Paged.js 输出为准，不依赖浏览器默认页眉页脚。

### 图表与资源就绪

- 扩展 `src/views/home/composables/useEcharts.js`，以受控方法暴露 ECharts `getDataURL`；`ReportChart.vue` 通过 `defineExpose()` 提供 `toPrintImage()`，不让外部读取私有实例。
- 网页仍使用交互式 ECharts；导出副本按 DOM/组件顺序将图表替换为 2x（必要时 3x）PNG，保证分页稳定和打印清晰。标题、表格、AI 文本继续保持真实可搜索文本；仅图表内部文字为图片。
- 启动 Paged.js 前依次等待：报告加载、`nextTick()`、图表渲染与 PNG 生成、`document.fonts.ready`、封面及所有图片 `decode/load`、导出容器附着并获得真实布局宽度。
- 导出过程防并发；在关闭、`afterprint`、异常和组件卸载时清理临时源、分页输出、监听器、状态与 URL。超出单页高度的长 AI 卡允许自然拆分，不能通过无限缩字强行不拆。

## 7. 图标与可访问性

- 仅在一级章节、AI 分析、风险/提示处复用现有 Element Plus 线性图标；普通表格、图表和三级标题不加图标。
- 图标不使用 emoji，不新增图标依赖；装饰性图标 `aria-hidden`，按钮保留文本/可访问名称和清晰焦点态。
- 分页预览提供明确的“打印/保存 PDF”“关闭”操作及生成中/失败反馈。

## 8. 测试与验证

### 自动测试

- 更新 `tests/report-preview.spec.js`：
  - 封面英文眉题、摘要卡、七个 `CHAPTER 01–07` 与原中文章名；
  - 原有字段、顺序、六类图表 kind 和图表业务断言全部保留；
  - 卡外唯一二级标题、ChartCard/解释区、独立 AI 卡、表格数字 class 和结论强调；
  - 导出入口触发分页预览而非直接 `window.print()`。
- 新增 `tests/report-markdown.spec.js`：验证允许的标题/段落/加粗/列表/引用/行内代码；原始 HTML 被当作文本；script、事件属性、图片、表格、代码块不形成对应 DOM；Markdown 链接无 `a[href]`；空文本 fallback 正确。
- 保留/补强首页 AI 纯文本测试，证明 `AiAnswerContent.vue` 没有受报告 Markdown 影响。
- 新增分页导出 composable 测试：
  - 封面、正文各调用一次 Previewer 且顺序正确；
  - 正文源包含 running header/footer 和章节 string class；
  - canvas 均被快照图片替换；
  - 字体/图片就绪前不分页；
  - 失败、关闭、afterprint 和重复点击时正确清理/防并发。
- 运行 `npm test` 与 `npm run build`。

### 真实浏览器/PDF 验收

- 用正式/冻结报告样本在 Chrome 与 Edge 检查：
  - 封面标题和摘要卡不遮挡 AI 地球、储能柜、风光电网；底部与正文底色自然衔接；
  - 网页正文比现版宽约 15%，窄屏无页面级横向溢出；
  - 表格对齐、斑马纹、关键值强调；六类图表数据、警戒线与语义色不变；
  - 分页预览第一页仅封面且无页眉页脚；正文第一页显示“第 1 页”；每页章节页眉随一级章变化；页脚单位与页码正确；
  - 七章新页、长表重复表头、标题不孤页、正常长度图表/AI卡不被截断；
  - 图表 PNG 清晰无空白；正文、表格、标题和 AI 文本可在 PDF 中选择、复制、搜索；
  - 浏览器默认页眉页脚关闭，背景图形开启。
- 特别覆盖：长项目名、长编制单位、18 行以上边界表、超长 AI Markdown、缺失 AI/图表数据、取消打印、重复导出与分页失败恢复。

## 9. 文档同步

报告主链路、组件结构和 PDF 导出方式属于主要模块结构变化；完成后按项目规则更新 `my_projects/investment-research-agent-项目开发指南.md` 的前端报告模块与验证章节，只记录架构、关键文件和运行方式，不写本机素材绝对路径或敏感配置。

## 关键文件

- `agent-frontend/src/views/report/index.vue`
- `agent-frontend/src/views/report/components/ReportChart.vue`
- `agent-frontend/src/views/home/composables/useEcharts.js`
- `agent-frontend/src/styles/report-print.css`
- `agent-frontend/src/design-system/tokens.css`
- `agent-frontend/tests/report-preview.spec.js`
- `agent-frontend/package.json`
- `agent-frontend/package-lock.json`
- `my_projects/investment-research-agent-项目开发指南.md`
