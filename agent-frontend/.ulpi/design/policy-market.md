---
feature: policy-market
binds_to: DESIGN.md
status: locked
---

# 政策与市场工作台

## 目标

让储能投资研究人员在一屏内完成三个连续动作：找到历史问题、提出新的研究问题、参考最新政策材料。页面首先服务提问，历史和资讯作为左右证据栏辅助，不与主任务争夺焦点。

## 信息架构

1. **案卷索引**：历史咨询，宽屏固定左栏；当前项用 accent 底线和轻底色识别。
2. **研究任务台**：标题、提问器、分析结果。证据脊线贯穿提问器与结果区，宽屏不封顶，优先吸收新增空间。
3. **材料流**：资讯统计、三个筛选条件、政策清单，宽屏固定右栏。

禁止：贯穿整页的左右大色柱、居中营销式英雄区、编号 eyebrow、嵌套卡片、无意义装饰。

## Flow: 发起政策研究

**目标：** 用户以最少认知成本提交一个政策或市场问题并读取结论。

**入口：** `/policy-market`、历史咨询项、新建提问按钮、快捷问题。

**步骤：**

1. 页面加载历史、当前咨询、统计和资讯；有当前案卷时直接进入阅读状态。
2. 用户输入或选择快捷问题。
3. `Ctrl/Cmd + Enter` 或点击“提交研究”。空输入只聚焦，不发送。
4. 提交后显示正在分析状态，通过 `aria-live` 宣告。
5. 成功后在证据脊线下展示结论、来源、范围和提醒；失败时提供明确错误状态。
6. 点击历史案卷后隐藏提问器，结论上移完整展开；点击“新建提问”恢复提问器并聚焦。

**边界状态：**

| 状态 | 处理 |
|---|---|
| 历史为空 | 左栏显示克制的空状态，新建按钮仍可用 |
| 数据加载 | 对应区域显示文本状态，不让布局跳动 |
| 请求失败 | 就地显示 danger 状态，保留输入与历史 |
| 刷新 | Store 重新加载并恢复后端当前数据 |
| 小屏 | 历史变为水平案卷条，材料流置于结果之后 |
| 小屏选择历史 | 自动将研究任务台滚动到可视区域顶部 |
| 超长标题 | 两行截断；正文允许自然换行 |

## 组件规范

### ConsultationComposer

- **目的：** 全页唯一主操作。
- **结构：** 证据脊线、标题“研究问题”、大输入区、快捷问题、提交区。
- **状态：** 默认、focus-within、空输入、已填写；按钮点击和快捷填充保持现有事件。
- **视觉：** `surface` 平面，不使用渐变；focus 时 accent 脊线变亮，阴影只用于此组件。
- **移动端：** 宽度 100%，提交按钮不小于 44px，高度稳定。
- **键盘：** Tab 可遍历；Ctrl/Cmd+Enter 提交；focus ring 清晰。

### ConsultationHistory

- **目的：** 快速返回既有案卷。
- **结构：** 标题、图标新建按钮、历史列表。
- **状态：** hover、focus、active、empty。
- **视觉：** 无外层卡片；每项使用分隔线，active 项使用 accent 左线和底色。
- **移动端：** 横向滚动，每项宽 200-240px，不形成页面横向溢出。

### ConsultationResult

- **目的：** 承接研究任务并呈现可信结论。
- **结构：** 状态标题、问题标题、正文、来源元数据。
- **状态：** empty、processing、failed、completed。
- **视觉：** 与提问器共享证据脊线，结果正文不放入装饰卡片。

### MarketPulse

- **目的：** 提供可筛选的政策材料流。
- **结构：** 栏标题、统计条、筛选组、资料列表。
- **状态：** loading、empty、error、可比趋势、无趋势。
- **视觉：** stats 使用一块真实工具容器；资料列表使用分隔线，不做重复卡片。
- **交互：** Element Plus Popover 保持现有行为；外链行为不变；自动滚动 hover/focus 时停止。
- **响应式：** 1024px 以下并入主流；640px 以下单列。

## Accessibility

- 正文与关键 UI 均达到 WCAG AA，具体对比见 `DESIGN.md`。
- 所有图标按钮提供中文 `aria-label` 与 `title`。
- 键盘焦点使用 2px accent，不以颜色之外的方式隐藏状态。
- 移动端交互目标至少 44px。
- 尊重 `prefers-reduced-motion`；状态变化通过现有 live region 宣告。

## Pre-Flight

- [x] 0 个规范外视觉值；一个 accent、一个圆角系统、一个图标系统
- [x] 0 个紫蓝渐变、渐变字、三等卡片、嵌套卡片、编号 eyebrow
- [x] 证据脊线签名明确且只出现于研究主流程
- [x] loading / empty / error / success 全覆盖
- [x] 键盘、ARIA、对比度、移动触控目标已规定
- [x] 三种布局家族：案卷索引、任务台、分隔线材料流
- [x] 每屏只有“提交研究”一个主操作

自评：distinctiveness 4；hierarchy 4；consistency 4；accessibility 4；state coverage 4；copy 4；restraint 4；motion 3。总分 31/32，无轴低于 3。

## Build Handoff

- target agent: Vue/Vite senior frontend engineer（当前 Codex 工程阶段）
- design system: 现有 Element Plus + `@lucide/vue`
- setup: 不新增 UI 框架；仅使用现有依赖并绑定锁定令牌
- instruction: Implement exactly this spec. Theme the design system with our locked tokens; do NOT redesign or re-implement its components.

### Acceptance Criteria

- [x] 宽屏三栏不形成色柱，主提问器为第一视觉焦点
- [x] 1280px 以下双栏、1100px 以下单工作区、640px 以下移动单栏，无页面横向滚动
- [x] 历史、快捷问题、提交、筛选、资讯链接、自动滚动功能不变
- [x] 结果四种状态均清晰
- [x] 生产构建与页面集成测试通过
- [ ] 内置浏览器宽屏和移动端截图无重叠、裁切或空白

Every screen must read as the same product if placed side by side.
