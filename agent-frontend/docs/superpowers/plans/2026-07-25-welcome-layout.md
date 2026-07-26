# Welcome Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move welcome-page platform metrics into the top bar and reposition the left-aligned welcome content into the upper-middle visual area without changing XC design language or behavior.

**Architecture:** `src/layout/index.vue` owns the global top bar and therefore becomes the single owner of welcome-only metric data and rendering. `src/views/home/index.vue` remains responsible for the conversation welcome surface, but removes its local metrics and changes only its vertical positioning. Existing Pinia state (`calc.messages`) remains the sole condition determining whether the welcome state is active.

**Tech Stack:** Vue 3 Composition API, Vite, Pinia, Vitest, Vue Test Utils, XC CSS custom-property tokens.

## Global Constraints

- Only render the metric strip when `route.name === 'Home'` and `calc.messages.length === 0`.
- Keep all five existing metric labels, values, units, and SVG icons as local display constants; do not introduce an API or new store state.
- Keep the welcome heading, lead, ability labels, `ChatComposer`, examples, and their existing behavior unchanged.
- Preserve left alignment and existing background-resource ownership in `Layout`.
- Use existing `--xc-*` tokens only; do not introduce inline hex/rgb colors or new visual language.
- Do not alter rail, history sidebar, conversation state, report pages, or non-welcome top-bar behavior.
- Use npm for frontend commands. Do not run Git write operations (`git add`, `git commit`, or `git push`).

---

## File Structure

- Modify: `src/layout/index.vue` — conditionally render the welcome-only top-bar metric strip, hold metric constants, and apply token-based strip styles.
- Modify: `src/views/home/index.vue` — remove local metric markup/data/styles and position existing welcome content in the content area's upper-middle section.
- Modify: `tests/layout-welcome-backdrop.spec.js` — extend layout-level coverage for welcome-only metric-strip visibility and metric count.
- Modify: `tests/home-welcome.spec.js` — assert that `Home` no longer owns the metric strip while retaining welcome behavior coverage.

### Task 1: Move Welcome Metrics to the Layout Top Bar

**Files:**
- Modify: `src/layout/index.vue:11-21`
- Modify: `src/layout/index.vue:68-89`
- Modify: `src/layout/index.vue:162-211`
- Test: `tests/layout-welcome-backdrop.spec.js:46-80`

**Interfaces:**
- Consumes: `showWelcomeBackdrop: ComputedRef<boolean>`, which is true only for the Home route with no calculation messages.
- Produces: `.ir-layout__welcome-metrics` containing exactly five `.ir-layout__welcome-metric` elements during welcome state; absent otherwise.

- [ ] **Step 1: Write failing layout visibility tests**

  In `tests/layout-welcome-backdrop.spec.js`, add one test after the welcome-backdrop test that mounts the Home route with `calc.messages = []` and asserts the strip and all five entries exist:

  ```js
  it('首页欢迎态在顶部栏展示五项平台指标', () => {
    const wrapper = mountLayout()

    expect(wrapper.find('.ir-layout__welcome-metrics').exists()).toBe(true)
    expect(wrapper.findAll('.ir-layout__welcome-metric')).toHaveLength(5)
    expect(wrapper.text()).toContain('累计测算次数')
    expect(wrapper.text()).toContain('覆盖省份')
  })
  ```

  Add one assertion to each existing non-welcome test to ensure the strip is not displayed:

  ```js
  expect(wrapper.find('.ir-layout__welcome-metrics').exists()).toBe(false)
  ```

- [ ] **Step 2: Run the layout test to verify it fails**

  Run:

  ```bash
  npm exec vitest -- run tests/layout-welcome-backdrop.spec.js
  ```

  Expected: FAIL because `.ir-layout__welcome-metrics` is not rendered by `Layout`.

- [ ] **Step 3: Add the metric strip template and metric constants**

  In `src/layout/index.vue`, add the following block between `.ir-brand` and `.ir-layout__user` inside `.ir-layout__topbar`:

  ```vue
  <div v-if="showWelcomeBackdrop" class="ir-layout__welcome-metrics" aria-label="平台概览">
    <div v-for="metric in metrics" :key="metric.label" class="ir-layout__welcome-metric">
      <span class="ir-layout__welcome-metric-icon" v-html="metric.icon" aria-hidden="true" />
      <span class="ir-layout__welcome-metric-copy">
        <span class="ir-layout__welcome-metric-label">{{ metric.label }}</span>
        <strong class="ir-layout__welcome-metric-value xc-num">{{ metric.value }}<em>{{ metric.unit }}</em></strong>
      </span>
    </div>
  </div>
  ```

  Add the existing five metric objects as `const metrics = [...]` near other top-level layout constants. Copy labels, values, units, and SVG strings exactly from the current `Home` component so the visible metric data does not change.

- [ ] **Step 4: Add token-based top-bar metric styles**

  In `src/layout/index.vue` scoped styles, introduce `.ir-layout__welcome-metrics` as a flexible horizontal group between brand and user. Use existing spacing, surface, border, radius, text, and accent tokens. Make each `.ir-layout__welcome-metric` flex evenly with a left divider except for the first entry. Reuse the current metric's visual proportions: a compact icon surface, stacked label/value text, and small unit text.

  Add a narrow-screen media query that allows the metric group to scroll horizontally or hides only the metric group below the established mobile breakpoint; choose hiding below `640px` so the top bar retains an accessible brand and user entry without overflow:

  ```css
  @media (max-width: 640px) {
    .ir-layout__welcome-metrics { display: none; }
  }
  ```

- [ ] **Step 5: Run the layout test to verify it passes**

  Run:

  ```bash
  npm exec vitest -- run tests/layout-welcome-backdrop.spec.js
  ```

  Expected: PASS, including welcome-only strip visibility and five-metric assertions.

### Task 2: Simplify Home Ownership and Reposition Welcome Content

**Files:**
- Modify: `src/views/home/index.vue:6-57`
- Modify: `src/views/home/index.vue:205-227`
- Modify: `src/views/home/index.vue:267-428`
- Test: `tests/home-welcome.spec.js:49-69`

**Interfaces:**
- Consumes: Existing `calc.responding` and `onSend(text)` behavior; no new props, events, stores, or APIs.
- Produces: `.ir-welcome__inner` remains the left-aligned welcome content surface; `Home` no longer renders or defines welcome metrics.

- [ ] **Step 1: Write failing Home ownership test**

  In `tests/home-welcome.spec.js`, add this test before the existing send-flow test:

  ```js
  it('keeps platform metrics out of the home welcome component', () => {
    const wrapper = mount(Home, { global: { stubs: {} } })

    expect(wrapper.find('.ir-welcome__metrics').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('累计测算次数')
  })
  ```

  This test should initially fail because metrics are still rendered by `Home`.

- [ ] **Step 2: Run the Home test to verify it fails**

  Run:

  ```bash
  npm exec vitest -- run tests/home-welcome.spec.js
  ```

  Expected: FAIL in `keeps platform metrics out of the home welcome component` because `.ir-welcome__metrics` exists.

- [ ] **Step 3: Remove local metric rendering and data**

  In `src/views/home/index.vue`:

  1. Remove the complete `<div class="ir-welcome__metrics" ...>` block after `.ir-welcome__inner`.
  2. Remove the `const metrics = [...]` display-only constant.
  3. Remove every `.ir-welcome__metrics`, `.ir-welcome__metric`, `.ir-welcome__metric-icon`, `.ir-welcome__metric-copy`, `.ir-welcome__metric-label`, and `.ir-welcome__metric-value` CSS rule, including their mobile overrides.

  Do not change the heading, lead, abilities, `ChatComposer`, example chips, `onSend`, or any conversation-state markup.

- [ ] **Step 4: Reposition the existing left-aligned welcome content**

  Update `.ir-welcome` and `.ir-welcome__inner` styles in `src/views/home/index.vue` so that the content is no longer pushed to the bottom by `margin-top: auto`.

  Replace the existing `margin-top: auto` on `.ir-welcome__inner` with a viewport-relative upper-middle offset, retaining `width: 100%` and `text-align: left`:

  ```css
  .ir-welcome__inner {
    position: relative;
    z-index: 1;
    width: 100%;
    margin-top: clamp(84px, 15vh, 168px);
    text-align: left;
  }
  ```

  Keep `.ir-welcome` as a left-aligned flex container and remove its need for a bottom metrics area. At the existing `max-width: 640px` breakpoint, override this offset to maintain room for the title and composer:

  ```css
  .ir-welcome__inner { margin-top: var(--xc-space-8); }
  ```

  Use only existing XC spacing tokens and do not alter horizontal alignment.

- [ ] **Step 5: Run the Home test to verify it passes**

  Run:

  ```bash
  npm exec vitest -- run tests/home-welcome.spec.js
  ```

  Expected: PASS, including existing background-ownership and example-send tests.

### Task 3: Run Targeted Regression and Production Build Checks

**Files:**
- Verify only: `tests/layout-welcome-backdrop.spec.js`
- Verify only: `tests/home-welcome.spec.js`
- Verify only: `tests/layout-sidebar.spec.js`
- Verify only: `package.json`

**Interfaces:**
- Consumes: Completed layout and Home changes from Tasks 1 and 2.
- Produces: Evidence that welcome conditional rendering, sidebar behavior, and production compilation remain intact.

- [ ] **Step 1: Run the focused welcome and sidebar tests**

  Run:

  ```bash
  npm exec vitest -- run tests/layout-welcome-backdrop.spec.js tests/home-welcome.spec.js tests/layout-sidebar.spec.js
  ```

  Expected: PASS. This verifies conditional welcome rendering, preserved example sending, and no regression in sidebar behavior.

- [ ] **Step 2: Run the full frontend test suite**

  Run:

  ```bash
  npm test
  ```

  Expected: PASS. If an unrelated existing failure occurs, record its test name and output without changing unrelated code.

- [ ] **Step 3: Run the production build**

  Run:

  ```bash
  npm run build
  ```

  Expected: exit code `0` and generated `dist/` output; no Vue template, scoped-style, or asset compilation errors.

- [ ] **Step 4: Inspect the final diff without Git writes**

  Run:

  ```bash
  git diff -- src/layout/index.vue src/views/home/index.vue tests/layout-welcome-backdrop.spec.js tests/home-welcome.spec.js
  ```

  Expected: only the approved welcome-metric relocation, upper-middle welcome positioning, and focused test coverage changes.
