# 隐藏研究案卷滚动条 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 隐藏政策与市场页面研究案卷历史记录列表的原生滚动条，同时保持全部现有滚动和业务交互。

**Architecture:** 这是局部样式变更，只调整 `ConsultationHistory.vue` 的 `.pm-history__list` 桌面端滚动容器规则。保留 `overflow-y: auto` 和移动端断点规则；通过 Firefox 与 Chromium/WebKit 的浏览器专属样式移除原生滚动条视觉元素，不改模板、组件属性或事件。

**Tech Stack:** Vue 3 SFC、scoped CSS、Vitest、Vue Test Utils。

---

## 文件结构

- 修改：`agent-frontend/src/views/policy-market/components/ConsultationHistory.vue`
  - 保留历史列表的垂直溢出滚动，替换 Firefox 的细滚动条显示规则，并补充 WebKit 滚动条隐藏规则。
- 验证：`agent-frontend/tests/policy-market-components.spec.js`
  - 使用既有历史列表交互用例确认模板、事件和滚动容器选择器未受样式修改影响；本次仅为 CSS 浏览器渲染规则，不增加脆弱的 SFC 样式文本断言。

### Task 1：隐藏桌面端历史列表原生滚动条

**Files:**
- Modify: `agent-frontend/src/views/policy-market/components/ConsultationHistory.vue:54-55`
- Test: `agent-frontend/tests/policy-market-components.spec.js:44-51`

- [ ] **Step 1：确认现有组件交互测试通过**

从 `agent-frontend/` 执行：

```bash
npm exec vitest -- run tests/policy-market-components.spec.js
```

预期：测试通过，且包含 `历史列表发出新建和选择事件，不渲染删除动作`。

- [ ] **Step 2：以最小 CSS 改动隐藏 Firefox 和 Chromium/WebKit 的滚动条**

在 `agent-frontend/src/views/policy-market/components/ConsultationHistory.vue` 的 scoped `<style>` 中，将当前规则：

```css
.pm-history__list { display: grid; max-height: calc(100vh - 190px); margin-top: 18px; overflow-y: auto; scrollbar-width: thin; }
```

替换为：

```css
.pm-history__list { display: grid; max-height: calc(100vh - 190px); margin-top: 18px; overflow-y: auto; scrollbar-width: none; }
.pm-history__list::-webkit-scrollbar { display: none; }
```

不得修改 `overflow-y: auto`，不得为容器增加 `overflow: hidden`，不得调整 `max-height`、间距或移动端媒体查询中的横向滚动规则。

- [ ] **Step 3：重新执行组件测试**

从 `agent-frontend/` 执行：

```bash
npm exec vitest -- run tests/policy-market-components.spec.js
```

预期：全部测试通过；历史列表的新建和选择事件仍正常发出。

- [ ] **Step 4：执行前端生产构建**

从 `agent-frontend/` 执行：

```bash
npm run build
```

预期：Vite 构建成功退出，无 CSS 编译错误。

- [ ] **Step 5：人工验收浏览器滚动行为**

从 `agent-frontend/` 执行：

```bash
npm run dev
```

打开 `http://localhost:5210/investment/`，进入“政策与市场”。准备足以使“研究案卷”列表溢出的历史记录后，核对：

1. 桌面端列表右侧不显示原生细滚动条。
2. 鼠标滚轮、触控板与键盘焦点滚动仍可访问列表中的全部记录。
3. 小于等于 1100px 宽度时，列表仍按原规则横向滚动，未被本次桌面端规则破坏。
4. 新建提问、选中一条历史记录及选中态展示均保持原样。

- [ ] **Step 6：记录验证结果，不执行 Git 写操作**

项目约束要求未经明确指示不得执行 `git add`、`git commit` 或 `git push`。在交付信息中列出组件测试、生产构建与人工验收的实际结果；不要创建提交。

## 自检

- 设计说明的四项验收标准均由 Task 1 的实现与验证步骤覆盖。
- 未新增依赖、组件、数据流、自定义进度指示器或不相关重构。
- CSS 属性、类名和文件路径均与当前源码一致；未包含 TBD、TODO 或未定义的实现步骤。
