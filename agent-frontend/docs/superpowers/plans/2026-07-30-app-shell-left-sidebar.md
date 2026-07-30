# AppShell Left Sidebar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the separate top bar, AppRail, and history panel with one reference-inspired left AppShell while preserving dynamic navigation, conversation history, welcome metrics, and report behavior.

**Architecture:** `AppSidebar.vue` becomes the single presentation component for brand, primary action, dynamic module navigation, history, and user identity. `layout/index.vue` remains the orchestration boundary for stores, routing, dialogs, welcome metrics, responsive drawer state, and the report-view exception; no API or store contracts change.

**Tech Stack:** Vue 3 Composition API, Vue Router 4, Pinia, Element Plus, Vitest, Vue Test Utils, XC CSS tokens, npm.

## Global Constraints

- Work inline on the current branch; do not create a worktree.
- Do not run `git add`, `git commit`, or `git push` because the repository forbids Git writes without a separate explicit request.
- Use `npm` for all frontend commands and add no dependencies.
- Preserve routes, icons, disabled state, and permission-store data; normalize only the three approved display labels and two approved menu markers by route.
- Preserve conversation replay, rename, confirmed soft deletion, current-user filtering, and welcome-page list loading.
- Preserve the five welcome metrics by moving them into the main content column.
- Preserve the report detail page as a shell-free full-width view.
- Use XC tokens for color, spacing, radius, shadow, and motion; do not introduce scattered hexadecimal colors.
- Use stable widths of 300px expanded and 68px compact, plus a modal drawer below 768px.
- New chat and history replay must finish on `/home`; normal module navigation keeps the existing route mapping.

---

### Task 1: Lock the Integrated AppShell Contract With Failing Tests

**Files:**
- Create: `agent-frontend/tests/app-shell.spec.js`
- Modify: `agent-frontend/tests/conversation-history.spec.js`
- Modify: `agent-frontend/tests/layout-sidebar.spec.js`
- Delete after replacement: `agent-frontend/tests/app-rail.spec.js`

**Interfaces:**
- Consumes: existing `AppSidebar` props `history`, `current` and history events.
- Produces: tested target props `items`, `active`, `username`, `userAvatar`, `collapsed`, `drawerOpen`; events `nav`, `new-chat`, `open-history`, `rename-history`, `delete-history`, `update:collapsed`, `close-drawer`.

- [ ] **Step 1: Write the failing integrated shell test**

```js
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AppSidebar from '@/layout/components/AppSidebar.vue'

const items = [
  { key: 'home', path: '/home', label: '对话首页', icon: 'home' },
  { key: 'line', path: '/tie-line', label: '联络线地图', icon: 'line' },
]

describe('AppShell left sidebar', () => {
  it('orders brand, primary action, module navigation, history, and user identity', () => {
    const wrapper = mount(AppSidebar, {
      props: {
        items,
        active: 'line',
        history: [{ conversationId: 7, title: '甘肃储能测算' }],
        username: '研究员',
        userAvatar: '/avatar.png',
      },
    })

    const shell = wrapper.find('[data-testid="app-shell"]')
    expect(shell.find('.ir-shell__brand').exists()).toBe(true)
    expect(shell.find('.ir-shell__new').text()).toContain('新建会话')
    expect(shell.findAll('.ir-shell__nav-item')).toHaveLength(2)
    expect(shell.find('.ir-shell__nav-item.is-active').text()).toContain('联络线地图')
    expect(shell.find('.ir-shell__history-title').text()).toBe('历史测算')
    expect(shell.find('.ir-shell__user').text()).toContain('研究员')
  })

  it('emits route targets and explicit compact-state changes', async () => {
    const wrapper = mount(AppSidebar, { props: { items, active: 'home' } })
    await wrapper.findAll('.ir-shell__nav-item')[1].trigger('click')
    await wrapper.find('.ir-shell__toggle').trigger('click')
    expect(wrapper.emitted('nav')).toEqual([['/tie-line']])
    expect(wrapper.emitted('update:collapsed')).toEqual([[true]])
  })
})
```

- [ ] **Step 2: Update history ordering assertions**

```js
const labels = wrapper.findAll('.ir-shell__nav-item').map((node) => node.text())
expect(labels).toEqual(['首页', '全国指数地图', '联络线地图', '政策与市场'])
expect(wrapper.find('.ir-shell__nav').element.compareDocumentPosition(
  wrapper.find('.ir-shell__history').element,
) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
```

- [ ] **Step 3: Run focused tests and confirm the red state**

Run: `npm exec vitest -- run tests/app-shell.spec.js tests/conversation-history.spec.js tests/layout-sidebar.spec.js`

Expected: FAIL because `AppSidebar` does not yet accept navigation/user props and still uses the old hover-expand history panel.

---

### Task 2: Merge Module Navigation, History, and User Identity Into AppSidebar

**Files:**
- Modify: `agent-frontend/src/layout/components/AppSidebar.vue`
- Test: `agent-frontend/tests/app-shell.spec.js`
- Test: `agent-frontend/tests/conversation-history.spec.js`
- Test: `agent-frontend/tests/layout-sidebar.spec.js`

**Interfaces:**
- Consumes: `items: Array|null`, `active: string`, `history: Array`, `current: string|number|null`, `username: string`, `userAvatar: string`, `collapsed: boolean`, `drawerOpen: boolean`.
- Produces: `nav(target: string)`, `new-chat()`, `open-history(id)`, `rename-history(conversation)`, `delete-history(id)`, `update:collapsed(boolean)`, `close-drawer()`.

- [ ] **Step 1: Move the icon normalizer and fallback items from AppRail**

```js
const props = defineProps({
  items: { type: Array, default: null },
  active: { type: String, default: 'home' },
  history: { type: Array, default: () => [] },
  current: { type: [Number, String], default: null },
  username: { type: String, default: '访客' },
  userAvatar: { type: String, default: '' },
  collapsed: { type: Boolean, default: false },
  drawerOpen: { type: Boolean, default: false },
})

const navItems = computed(() => {
  const source = props.items?.length ? props.items : fallbackItems
  return source.map((item) => ({
    ...item,
    icon: item.icon?.startsWith('<svg') ? item.icon : ICON[item.icon] || ICON.default,
  }))
})
```

- [ ] **Step 2: Replace the old hover-expand template with the unified hierarchy**

```vue
<aside class="ir-shell" data-testid="app-shell">
  <header class="ir-shell__brand">
    <img class="ir-shell__logo" src="/brand-logo.svg" alt="" aria-hidden="true" />
    <span class="ir-shell__brand-copy">
      <strong>朱雀投研智能体</strong>
      <small>ZRA · STORAGE INVESTMENT AI</small>
    </span>
    <button class="ir-shell__toggle" type="button" aria-label="折叠侧栏" @click="$emit('update:collapsed', !collapsed)">
      <span aria-hidden="true">«</span>
    </button>
  </header>
  <button class="ir-shell__new" type="button" @click="$emit('new-chat')">
    <span aria-hidden="true">+</span><span class="ir-shell__label">新建会话</span>
  </button>
  <div class="ir-shell__section-title">投资分析工作台</div>
  <nav class="ir-shell__nav" aria-label="投资分析工作台">
    <button
      v-for="item in navItems"
      :key="item.key || item.path"
      class="ir-shell__nav-item"
      :class="{ 'is-active': (item.key || item.path) === active }"
      :aria-current="(item.key || item.path) === active ? 'page' : undefined"
      @click="onNav(item)"
    >
      <span class="ir-shell__nav-icon" v-html="item.icon" aria-hidden="true" />
      <span class="ir-shell__label">{{ item.label }}</span>
    </button>
  </nav>
  <section class="ir-shell__history">
    <div class="ir-shell__history-title">历史测算</div>
    <p v-if="!history.length" class="ir-shell__history-empty">暂无历史测算</p>
    <button
      v-for="conversation in history"
      :key="conversation.conversationId"
      class="ir-shell__history-item"
      type="button"
      @click="$emit('open-history', conversation.conversationId)"
    >
      <span class="ir-shell__history-name">{{ conversation.title || '未命名会话' }}</span>
    </button>
  </section>
  <footer class="ir-shell__user">
    <img :src="userAvatar" alt="" aria-hidden="true" />
    <span class="ir-shell__label">{{ username }}</span>
  </footer>
</aside>
```

- [ ] **Step 3: Implement stable expanded/compact/drawer styling**

```css
.ir-shell-wrap { width: var(--xc-sidebar-w); flex: 0 0 auto; transition: width var(--xc-dur-base) var(--xc-ease-out); }
.ir-shell-wrap.is-collapsed { width: 68px; }
.ir-shell { height: calc(100% - 24px); margin: 12px; padding: var(--xc-space-5); background: var(--xc-surface-sider); }
.ir-shell__new { width: 100%; height: 42px; background: var(--xc-grad-brand); }
.ir-shell__nav-item { width: 100%; min-height: 40px; background: transparent; }
.ir-shell__nav-item.is-active { background: var(--xc-surface-control); color: var(--xc-text-strong); }
.ir-shell-wrap.is-collapsed .ir-shell__label,
.ir-shell-wrap.is-collapsed .ir-shell__section-title,
.ir-shell-wrap.is-collapsed .ir-shell__history { display: none; }
.ir-shell button:focus-visible { outline: 2px solid var(--xc-accent-blue); outline-offset: 2px; }
@media (prefers-reduced-motion: reduce) { .ir-shell-wrap { transition: none; } }
```

- [ ] **Step 4: Run focused tests and confirm green**

Run: `npm exec vitest -- run tests/app-shell.spec.js tests/conversation-history.spec.js tests/layout-sidebar.spec.js`

Expected: PASS.

---

### Task 3: Put AppShell in the Left Layout and Preserve Existing Page Behavior

**Files:**
- Modify: `agent-frontend/src/layout/index.vue`
- Modify: `agent-frontend/tests/layout-welcome-backdrop.spec.js`
- Modify: `agent-frontend/tests/logo-mask.spec.js`
- Create: `agent-frontend/tests/layout-app-shell.spec.js`

**Interfaces:**
- Consumes: permission store `railRoutes`, session store `username`, calculation store history/actions, `route.meta.collapseSidebar`.
- Produces: left-column AppShell orchestration, `/home` routing after new/replay, welcome metrics in the main column, responsive drawer controls.

- [ ] **Step 1: Write failing layout assertions**

```js
it('renders one shell beside the content instead of a top bar and AppRail', () => {
  const wrapper = mountLayout()
  expect(wrapper.find('.ir-layout__topbar').exists()).toBe(false)
  expect(wrapper.find('.app-rail-stub').exists()).toBe(false)
  expect(wrapper.find('.app-sidebar-stub').exists()).toBe(true)
  expect(wrapper.find('.ir-layout__content').exists()).toBe(true)
})

it('returns to home for a new chat and successful history replay', async () => {
  const wrapper = mountLayout()
  wrapper.findComponent(AppSidebarStub).vm.$emit('new-chat')
  await nextTick()
  expect(calc.resetConversation).toHaveBeenCalled()
  expect(router.push).toHaveBeenCalledWith('/home')

  wrapper.findComponent(AppSidebarStub).vm.$emit('open-history', 7)
  await flushPromises()
  expect(calc.openConversation).toHaveBeenCalledWith(7)
  expect(router.push).toHaveBeenCalledWith('/home')
})
```

- [ ] **Step 2: Replace the column structure**

```vue
<div class="ir-layout__body" :class="{ 'is-report-view': isReportView }">
  <AppSidebar
    v-if="!isReportView"
    v-model:collapsed="sidebarCollapsed"
    :drawer-open="drawerOpen"
    :items="navItems"
    :active="activeRail"
    :history="calc.history"
    :current="calc.conversationId"
    :username="session.username || '访客'"
    :user-avatar="userAvatar"
    @nav="onNav"
    @new-chat="onNewChat"
    @open-history="onOpenHistory"
    @close-drawer="closeDrawer"
  />
  <section class="ir-layout__content">
    <div v-if="isWelcome" class="ir-layout__welcome-metrics" aria-label="平台概览">
      <div v-for="metric in metrics" :key="metric.label" class="ir-layout__welcome-metric">
        <span class="ir-layout__welcome-metric-icon" v-html="metric.icon" aria-hidden="true" />
        <span class="ir-layout__welcome-metric-copy">
          <span class="ir-layout__welcome-metric-label">{{ metric.label }}</span>
          <strong class="ir-layout__welcome-metric-value xc-num">{{ metric.value }}<em>{{ metric.unit }}</em></strong>
        </span>
      </div>
    </div>
    <main class="ir-layout__viewport"><router-view /></main>
  </section>
</div>
```

- [ ] **Step 3: Implement route and drawer behavior**

```js
async function goHome() {
  if (router.currentRoute.value.path !== '/home') await router.push('/home')
  drawerOpen.value = false
}

async function onNewChat() {
  calc.resetConversation()
  await goHome()
}

async function onOpenHistory(conversationId) {
  try {
    await calc.openConversation(conversationId)
    await goHome()
  } catch {
    ElMessage.error('打开历史会话失败，请稍后重试')
  }
}
```

Add an Escape listener only while the drawer is open, return focus to the mobile menu trigger after closing, and close the drawer after all successful navigation actions.

- [ ] **Step 4: Preserve welcome metrics and report exception**

Keep all five existing `metrics` entries and their rendering under `.ir-layout__content`. For `ReportDetail`, render no AppShell/mobile trigger and let `.ir-layout__content` occupy the full viewport.

- [ ] **Step 5: Run layout and brand tests**

Run: `npm exec vitest -- run tests/layout-app-shell.spec.js tests/layout-welcome-backdrop.spec.js tests/logo-mask.spec.js`

Expected: PASS.

---

### Task 4: Remove the Obsolete Rail and Verify the Complete Frontend

**Files:**
- Delete: `agent-frontend/src/layout/components/AppRail.vue`
- Delete: `agent-frontend/tests/app-rail.spec.js`
- Modify only if visual QA exposes a scoped issue: `agent-frontend/src/layout/index.vue`
- Modify only if visual QA exposes a scoped issue: `agent-frontend/src/layout/components/AppSidebar.vue`

**Interfaces:**
- Consumes: completed Tasks 1-3.
- Produces: one AppShell implementation with no stale AppRail consumer.

- [ ] **Step 1: Confirm AppRail has no remaining consumers**

Run: `rg -n "AppRail|ir-rail" agent-frontend/src agent-frontend/tests`

Expected: only the obsolete component/test appear before deletion; no output after deletion.

- [ ] **Step 2: Run the complete unit suite**

Run: `npm test`

Expected: all Vitest suites pass.

- [ ] **Step 3: Build production assets**

Run: `npm run build`

Expected: Vite exits with code 0 and produces `dist/` without unresolved component or CSS errors.

- [ ] **Step 4: Start the development server**

Run: `npm run dev -- --host 127.0.0.1`

Expected: Vite serves the application on port 5210 or the next available port.

- [ ] **Step 5: Verify responsive layouts in a real browser**

Capture and inspect the home page at 1440x900, 1024x768, and 390x844. Confirm the shell is nonblank, desktop/compact/drawer widths are stable, the active row is visible, the welcome metrics remain in the content column, text does not overflow, the mobile drawer does not cover its own close control, and the report route remains full width.

- [ ] **Step 6: Run final diff checks**

Run: `git diff --check && git status --short`

Expected: no whitespace errors; only the approved AppShell implementation, tests, design, and plan are modified.

---

### Task 5: Apply the Approved Menu Names and Right-Aligned Markers

**Files:**
- Modify: `agent-frontend/src/layout/components/AppSidebar.vue`
- Modify: `agent-frontend/tests/app-shell.spec.js`

**Interfaces:**
- Consumes: dynamic or fallback menu items with existing `{ key, path, label, icon }` fields.
- Produces: normalized presentation items where `/home` is `{ label: '朱雀星核', meta: '引擎' }`, `/index-map` is `{ label: '朱雀寻龙图', meta: 'MAP' }`, and `/policy-market` is `{ label: '专业数据速查' }`; emitted navigation targets remain unchanged.

- [ ] **Step 1: Write the failing presentation test**

```js
it('normalizes approved menu names and right-side markers by route', () => {
  const wrapper = mount(AppSidebar, {
    props: {
      items: [
        { path: '/home', label: '首页', icon: 'home' },
        { path: '/index-map', label: '全国指数地图', icon: 'index' },
        { path: '/policy-market', label: '政策与市场', icon: 'policy' },
      ],
    },
  })
  expect(wrapper.findAll('.ir-shell__nav-item').map((item) => item.text()))
    .toEqual(['朱雀星核引擎', '朱雀寻龙图MAP', '专业数据速查'])
  expect(wrapper.findAll('.ir-shell__nav-meta').map((item) => item.text()))
    .toEqual(['引擎', 'MAP'])
})
```

- [ ] **Step 2: Run the test and verify RED**

Run: `npm exec vitest -- run tests/app-shell.spec.js -t "normalizes approved menu names"`

Expected: FAIL because the current component renders backend labels and has no `.ir-shell__nav-meta` elements.

- [ ] **Step 3: Normalize display fields and render the marker**

```js
const MENU_PRESENTATION = {
  '/home': { label: '朱雀星核', meta: '引擎' },
  '/index-map': { label: '朱雀寻龙图', meta: 'MAP' },
  '/policy-market': { label: '专业数据速查' },
}

return source.map((item) => ({
  ...item,
  ...MENU_PRESENTATION[item.path],
  icon: item.icon?.startsWith('<svg') ? item.icon : ICON[item.icon] || ICON.default,
}))
```

Render `item.meta` after the primary label and style it with `margin-left: auto`, the existing muted text token, and a stable utility font size. Include the marker in the collapsed-state hidden selector.

- [ ] **Step 4: Run focused AppShell tests and verify GREEN**

Run: `npm exec vitest -- run tests/app-shell.spec.js tests/layout-app-shell.spec.js`

Expected: PASS with the new names, markers, unchanged route emission, drawer behavior, and route-persistent expanded state.
