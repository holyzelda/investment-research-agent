# XC Visual Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the investment research frontend to an XC-consistent institutional dark workspace with carefully limited brand signature focal points, while preserving all calculation and parameter-adjustment behavior.

**Architecture:** Extend the existing XC token layer with derived semantic surface tokens, then apply those tokens to the app shell, conversation layout, result report, charts, and parameter controls. No store, API, business rule, ECharts data-contract, or parameter-dictionary behavior changes; component structure evolves only where tests can continue to validate the existing user-visible behavior.

**Tech Stack:** Vue 3 Composition API, Vite 5, Element Plus, Pinia, ECharts 5, Vitest, Vue Test Utils, CSS custom properties.

## Global Constraints

- Do not use Spec-Superflow or modify its artifacts.
- Do not run `git add`, `git commit`, `git push`, or any Git write operation.
- Keep all component colors token-based: no new inline hex/rgb declarations and no Tailwind color classes.
- New visual tokens must be derived only from the existing XC dark palette, brand palette, borders, and shadows.
- Preserve API, Pinia, task polling, history replay, version selection, report placeholder, result snapshot, parameter dictionary, and recalculation behavior.
- Preserve `formatNumber` and `formatPrice` as the only number formatting utilities.
- Preserve `--xc-chart-*`, Chinese market red-up/green-down semantics, and the DSCR chart data and axis behavior.
- Use `pnpm` only. Run commands through `pnpm`.

---

## File Structure

| File | Responsibility |
|---|---|
| `src/design-system/tokens.css` | Own the additional XC-derived visual surface, gradient, and layout tokens shared by every component. |
| `src/layout/index.vue` | Establish the 64px application shell, atmospheric background, and quiet top-bar treatment. |
| `src/layout/components/AppRail.vue` | Apply the new quiet navigation surface and tokenized active treatment. |
| `src/layout/components/AppSidebar.vue` | Apply elevated-history-panel hierarchy while retaining all collapse and history interactions. |
| `src/views/home/index.vue` | Establish responsive shared content width, welcome-space hierarchy, message width, and version summary wording. |
| `src/views/home/components/ChatComposer.vue` | Align the composer with the shared column and quiet elevated control treatment. |
| `src/views/home/components/ResultCard.vue` | Turn the result into a state header plus separate elevated report modules. |
| `src/views/home/components/BasicInfoBlock.vue` | Present frozen project boundary information as an elevated report module. |
| `src/views/home/components/FinancialBlock.vue` | Present five enlarged KPIs and identify project IRR as the sole signature KPI. |
| `src/views/home/components/RevenueDonut.vue` | Provide an elevated chart-card treatment without changing donut data/options. |
| `src/views/home/components/DebtServiceCoverage.vue` | Provide an elevated chart-card treatment without changing DSCR math/options. |
| `src/views/home/components/ParamAdjustPanel.vue` | Turn inline parameter adjustment into grouped elevated control surfaces. |
| `src/views/home/components/AdvancedParamDialog.vue` | Turn the modal and its financial/revenue/cost sections into elevated control surfaces. |
| `tests/result-cards.spec.js` | Assert the visual-report semantic markers and preserve existing result behavior checks. |
| `tests/conversation-history.spec.js` | Update the version-summary expectation from capital IRR to project IRR if it asserts the old copy. |
| `tests/param-adjust-panel.spec.js` | Assert parameter control group markers while preserving behavior assertions. |
| `tests/advanced-param-dialog.spec.js` | Assert elevated section markers while preserving metadata-driven control behavior assertions. |

## Task 1: Add XC-derived surface and layout tokens

**Files:**
- Modify: `src/design-system/tokens.css:12-201`
- Test: `tests/scaffold.spec.js`

**Interfaces:**
- Consumes: existing `--xc-surface-*`, `--xc-border-*`, `--xc-brand-*`, `--xc-shadow-*`, and spacing tokens.
- Produces: `--xc-surface-workspace`, `--xc-surface-raised`, `--xc-surface-card`, `--xc-surface-control`, `--xc-border-card`, `--xc-shadow-raised`, `--xc-grad-atmosphere`, `--xc-content-max`, and `--xc-content-fluid` CSS custom properties.

- [ ] **Step 1: Write the failing token-contract test**

Add this test to `tests/scaffold.spec.js` using the project’s existing `fs`/path test style:

```js
it('defines the XC workspace elevation and responsive-content tokens', () => {
  const css = readFileSync(resolve(projectRoot, 'src/design-system/tokens.css'), 'utf8')

  for (const token of [
    '--xc-surface-workspace',
    '--xc-surface-raised',
    '--xc-surface-card',
    '--xc-surface-control',
    '--xc-border-card',
    '--xc-shadow-raised',
    '--xc-grad-atmosphere',
    '--xc-content-max',
    '--xc-content-fluid',
  ]) {
    expect(css).toContain(token)
  }
})
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `pnpm vitest run tests/scaffold.spec.js -t "workspace elevation"`

Expected: FAIL because `--xc-surface-workspace` and the other derived tokens do not exist.

- [ ] **Step 3: Add derived token definitions**

In the dark `:root` block, add this exact group after existing surface values:

```css
  /* ---------- 1.1 WORKSPACE ELEVATION (derived XC dark surfaces) ---------- */
  --xc-surface-workspace: rgba(10, 12, 18, 0.96);
  --xc-surface-raised: rgba(44, 46, 55, 0.92);
  --xc-surface-card: rgba(255, 255, 255, 0.055);
  --xc-surface-control: rgba(255, 255, 255, 0.075);
  --xc-border-card: rgba(212, 217, 229, 0.16);
```

After the existing shadow values, add:

```css
  --xc-shadow-raised: inset 0 1px 0 rgba(255, 255, 255, 0.045),
                      0 18px 48px rgba(0, 0, 0, 0.34);
```

After the named gradients, add:

```css
  --xc-grad-atmosphere: radial-gradient(circle at 8% 90%, rgba(0, 240, 253, 0.075), transparent 32%),
                        radial-gradient(circle at 92% 8%, rgba(110, 42, 255, 0.09), transparent 34%);
```

After layout constants, add:

```css
  --xc-content-max: 1100px;
  --xc-content-fluid: min(var(--xc-content-max), 88vw);
```

In `:root[data-theme="light"]`, provide semantic equivalents for all new surface and border tokens; keep `--xc-grad-atmosphere` transparent in light mode.

- [ ] **Step 4: Run the focused test to verify it passes**

Run: `pnpm vitest run tests/scaffold.spec.js -t "workspace elevation"`

Expected: PASS.

- [ ] **Step 5: Run the scaffold regression suite**

Run: `pnpm vitest run tests/scaffold.spec.js`

Expected: PASS.

## Task 2: Establish the atmospheric shell and quiet navigation surfaces

**Files:**
- Modify: `src/layout/index.vue:84-143`
- Modify: `src/layout/components/AppRail.vue:50-141`
- Modify: `src/layout/components/AppSidebar.vue:138-380`
- Test: `tests/app-rail.spec.js`
- Test: `tests/conversation-history.spec.js`

**Interfaces:**
- Consumes: Task 1 tokens, existing rail navigation emits, sidebar history props, collapse behavior, and history events.
- Produces: a 64px top bar, a non-interactive atmospheric workspace background, and tokenized quiet rail/sidebar surfaces.

- [ ] **Step 1: Write failing shell-structure tests**

Append to `tests/app-rail.spec.js`:

```js
it('keeps the rail navigation contract while using the workspace active marker', () => {
  const wrapper = mount(AppRail, { props: { active: 'home' } })

  expect(wrapper.find('.ir-rail-btn.is-active').attributes('aria-current')).toBe('page')
  expect(wrapper.find('.ir-rail-wrap').classes()).toContain('ir-rail-wrap')
})
```

Append to `tests/conversation-history.spec.js`:

```js
it('keeps the history sidebar available inside the elevated shell', () => {
  const wrapper = mount(AppSidebar, { props: { history: [], current: null } })

  expect(wrapper.find('.ir-sider').exists()).toBe(true)
  expect(wrapper.find('.ir-sider__new').text()).toContain('新建会话')
})
```

- [ ] **Step 2: Run the focused test files to verify the baseline**

Run: `pnpm vitest run tests/app-rail.spec.js tests/conversation-history.spec.js`

Expected: PASS before styling changes; these are regression guards for unchanged interactions.

- [ ] **Step 3: Implement the shell style changes**

In `src/layout/index.vue`, make the top bar `64px`, set `.ir-layout` background to `var(--xc-surface-workspace)`, and add a non-interactive pseudo-element background layer:

```css
.ir-layout {
  position: relative;
  isolation: isolate;
  background: var(--xc-surface-workspace);
}
.ir-layout::before {
  content: '';
  position: absolute;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  background: var(--xc-grad-atmosphere);
}
.ir-layout__topbar {
  height: 64px;
  padding: 0 var(--xc-gutter-x);
  background: transparent;
}
```

Add a compact brand-mark element before `.ir-brand__name` in the existing brand markup and style it with `var(--xc-grad-brand)`, `var(--xc-radius-sm)`, and no new literal color values. Give the user area a `var(--xc-surface-card)` background, `var(--xc-border-soft)` outline, `var(--xc-radius-full)` radius, and compact horizontal padding.

In `AppRail.vue`, replace direct surface literals with `--xc-surface-raised`, `--xc-surface-control`, `--xc-border-card`, and existing accent tokens. Preserve all dimensions, disabled behavior, tooltip behavior, and `aria-current` handling.

In `AppSidebar.vue`, replace direct dark surface/card literals with Task 1 tokens; use `--xc-shadow-raised` for the normal sidebar and existing `--xc-shadow-xl` for hover expansion. Preserve 300px width, collapse geometry, history events, delete menu, and all event handlers.

- [ ] **Step 4: Run shell behavior tests**

Run: `pnpm vitest run tests/app-rail.spec.js tests/conversation-history.spec.js`

Expected: PASS.

- [ ] **Step 5: Run a production build**

Run: `pnpm build`

Expected: exit code 0 and Vite production build output.

## Task 3: Unify responsive conversation width and refine the welcome state

**Files:**
- Modify: `src/views/home/index.vue:168-366`
- Modify: `src/views/home/components/ChatComposer.vue:55-124`
- Test: `tests/home.spec.js`

**Interfaces:**
- Consumes: `--xc-content-fluid`, existing `ChatComposer` props/events, calculation store `sendAndCalculate`, and example prompts.
- Produces: one responsive width contract shared by message rows, result cards, and composer; unchanged welcome and send behavior.

- [ ] **Step 1: Write failing layout-marker tests**

Add a component mount test to `tests/home.spec.js` after the existing store tests. Mock the calculation/session stores using the repository’s existing home-view test pattern, then assert:

```js
expect(wrapper.find('.ir-welcome').exists()).toBe(true)
expect(wrapper.find('.ir-welcome__composer').exists()).toBe(true)
expect(wrapper.findAll('.ir-chip')).toHaveLength(3)
```

Add a stylesheet-source assertion in the same test file:

```js
it('uses the shared responsive XC content width for conversation surfaces', () => {
  const source = readFileSync(resolve(projectRoot, 'src/views/home/index.vue'), 'utf8')
  expect(source).toContain('var(--xc-content-fluid)')
  expect(source).toContain('.ir-home__composer')
})
```

- [ ] **Step 2: Run the focused tests to verify the source assertion fails**

Run: `pnpm vitest run tests/home.spec.js -t "shared responsive XC content width"`

Expected: FAIL because `var(--xc-content-fluid)` is not used in `index.vue`.

- [ ] **Step 3: Implement shared width and welcome hierarchy**

In `src/views/home/index.vue`:

- Replace the 900px message maximum with `max-width: var(--xc-content-fluid)`.
- Make `.ir-home__composer` use the same `max-width: var(--xc-content-fluid)`; retain appropriate internal composer padding so its outer visual edge aligns with message rows.
- Keep avatar offsets outside the message row and increase stream side padding only enough to avoid clipping on the widest supported content width.
- Increase welcome vertical space with existing spacing tokens; retain the existing image, animation, title, lead, and chips.
- Replace literal border/background values in chips, user bubble, assistant bubble, version items, and selected result treatment with Task 1 tokens or existing XC tokens.
- Change the version summary copy from `资本金IRR` to `项目全投资IRR` and read `v.result?.financial?.projectIrr`.
- Keep the existing `selectVersion`, smooth scrolling, report placeholder, example-send, and calculation calls unchanged.

In `ChatComposer.vue`, replace all direct surface/border/shadow literals with `--xc-surface-raised`, `--xc-surface-control`, `--xc-border-card`, and `--xc-shadow-raised`. Preserve Enter/send, Shift+Enter, disabled state, v-model behavior, and send event.

- [ ] **Step 4: Run the home tests**

Run: `pnpm vitest run tests/home.spec.js`

Expected: PASS.

- [ ] **Step 5: Run the calculation flow regression**

Run: `pnpm vitest run tests/calc-flow.spec.js tests/version-list.spec.js`

Expected: PASS.

## Task 4: Convert the result into elevated report modules and make project IRR the signature KPI

**Files:**
- Modify: `src/views/home/components/ResultCard.vue:1-101`
- Modify: `src/views/home/components/BasicInfoBlock.vue:1-115`
- Modify: `src/views/home/components/FinancialBlock.vue:1-81`
- Test: `tests/result-cards.spec.js`

**Interfaces:**
- Consumes: unchanged `result`, `version`, `paramDict`, `seedInput`, `switches`, `stationOptions`, and `responding` props; unchanged `recalculate` and `open-advanced` behavior.
- Produces: `.ir-report-module`, `.ir-fin__kpi--signature`, and `.ir-result__head--complete` semantic style markers without changing result data or emitted events.

- [ ] **Step 1: Write failing result-report tests**

Extend the first `result-cards.spec.js` test:

```js
expect(wrapper.findAll('.ir-report-module')).toHaveLength(3)
expect(wrapper.find('.ir-result__head--complete').exists()).toBe(true)
expect(wrapper.find('.ir-fin__kpi--signature').text()).toContain('项目全投资IRR')
expect(wrapper.findAll('.ir-fin__kpi')).toHaveLength(5)
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `pnpm vitest run tests/result-cards.spec.js -t "renders basic information"`

Expected: FAIL because the report-module and signature KPI markers do not exist.

- [ ] **Step 3: Implement report modules and KPI hierarchy**

In `ResultCard.vue`:

- Change the state header class to include `ir-result__head--complete`.
- Remove divider-only layout; place BasicInfoBlock, FinancialBlock, and the advanced-analysis section as exactly three sibling elements marked `ir-report-module`.
- Keep `ParamAdjustPanel`, `AdvancedParamDialog`, warnings, report placeholder, computed values, watch, and emits unchanged.
- Set the outer result to an elevated shell using `--xc-surface-raised`, `--xc-border-card`, and `--xc-shadow-raised`; report modules use `--xc-surface-card`, `--xc-border-card`, and tokenized spacing.

In `BasicInfoBlock.vue`:

- Preserve title text, field order, conditionally hidden node, units, and `formatPriceUnit` behavior.
- Make `.ir-basic-card` the module body using task tokens; remove direct rgba literals.
- At constrained widths, allow both project-information rows to collapse from 4/3 columns to two columns and then one column without clipping.

In `FinancialBlock.vue`:

- Add `:class="{ 'ir-fin__kpi--signature': kpi.key === 'projectIrr' }"` to each KPI element.
- Add `key: 'projectIrr'` through `key: 'averageProfit'` to the five entries in `kpis`.
- Keep their current sequence and values.
- Make all values use `var(--xc-fs-kpi-md)` or an equivalent `clamp()` with a clearly larger minimum than the existing 18px.
- Apply brand gradient text and a subtle tokenized border/shadow only to `.ir-fin__kpi--signature .ir-fin__val`; keep the other KPI values `var(--xc-text-strong)` or another non-brand strong text token.
- Convert the KPI grid to responsive five-column / two-column / one-column behavior using CSS grid `minmax()` and media queries as needed.

- [ ] **Step 4: Run result-card tests**

Run: `pnpm vitest run tests/result-cards.spec.js`

Expected: PASS, including existing formatting assertions and new report markers.

- [ ] **Step 5: Run number-format regression tests**

Run: `pnpm vitest run tests/result-cards.spec.js tests/charts.spec.js`

Expected: PASS; snapshot values remain unmodified.

## Task 5: Elevate chart surfaces without changing chart contracts

**Files:**
- Modify: `src/views/home/components/RevenueDonut.vue:66-91`
- Modify: `src/views/home/components/DebtServiceCoverage.vue:133-144`
- Test: `tests/charts.spec.js`

**Interfaces:**
- Consumes: unchanged chart props, `useEcharts`, `xcChartColors`, `xcVar`, ECharts options, and DSCR mapping functions.
- Produces: chart cards with `.ir-chart--report` and unchanged chart configuration behavior.

- [ ] **Step 1: Write failing chart-card marker tests**

Add to `tests/charts.spec.js`:

```js
it('renders both analysis charts as elevated report cards', () => {
  const donut = mount(RevenueDonut, { props: { donut: { totalRevenue: 100 } } })
  const coverage = mount(DebtServiceCoverage, { props: { coverage: { cashflowRatio: [1, 1.2] } } })

  expect(donut.find('.ir-chart--report').exists()).toBe(true)
  expect(coverage.find('.ir-chart--report').exists()).toBe(true)
})
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `pnpm vitest run tests/charts.spec.js -t "elevated report cards"`

Expected: FAIL because neither chart root has `ir-chart--report`.

- [ ] **Step 3: Implement tokenized elevated chart cards**

In both chart templates, change the root class to `class="ir-chart ir-chart--report"`.

In each component stylesheet:

```css
.ir-chart--report {
  border: 1px solid var(--xc-border-card);
  border-radius: var(--xc-radius-lg);
  background: var(--xc-surface-card);
  box-shadow: var(--xc-shadow-sm);
  padding: var(--xc-space-7);
}
```

Remove direct card border/background literals. Keep RevenueDonut’s legend, series, color, data filtering, and sizing. Keep DebtServiceCoverage’s ratio mapping, mark line, mark area, safety series, tooltip, and axis behavior exactly as-is. Replace only the use of a nonexistent/misnamed surface variable if present with an available Task 1 surface token for point borders.

- [ ] **Step 4: Run chart tests**

Run: `pnpm vitest run tests/charts.spec.js`

Expected: PASS.

- [ ] **Step 5: Run result/chart integration regression**

Run: `pnpm vitest run tests/result-cards.spec.js tests/charts.spec.js`

Expected: PASS.

## Task 6: Cardify the inline parameter controls and advanced dialog

**Files:**
- Modify: `src/views/home/components/ParamAdjustPanel.vue:236-295`
- Modify: `src/views/home/components/AdvancedParamDialog.vue:163-201`
- Test: `tests/param-adjust-panel.spec.js`
- Test: `tests/advanced-param-dialog.spec.js`

**Interfaces:**
- Consumes: unchanged param dictionary metadata, existing `groupByZone`, `buildOverrides`, `dynamicRange`, `roundToStep`, dialog `save` event, and recalculation emit.
- Produces: `.ir-adjust__zone-card` and `.ir-advanced__section-card` style markers; unchanged dictionary-driven parameter functionality.

- [ ] **Step 1: Write failing control-surface tests**

In `tests/param-adjust-panel.spec.js`, add:

```js
it('renders each visible parameter zone inside an elevated control surface', async () => {
  const wrapper = mount(ParamAdjustPanel, { props: panelProps })
  await wrapper.find('.ir-adjust__toggle').trigger('click')

  expect(wrapper.findAll('.ir-adjust__zone-card').length).toBeGreaterThan(0)
})
```

In `tests/advanced-param-dialog.spec.js`, add this assertion in the section-order test:

```js
expect(sections.every((section) => section.classes().includes('ir-advanced__section-card'))).toBe(true)
```

- [ ] **Step 2: Run focused parameter tests to verify they fail**

Run: `pnpm vitest run tests/param-adjust-panel.spec.js tests/advanced-param-dialog.spec.js`

Expected: FAIL because the card marker classes do not yet exist.

- [ ] **Step 3: Implement inline parameter zone cards**

In `ParamAdjustPanel.vue`, add `ir-adjust__zone-card` to each existing `.ir-adjust__zone` section class binding. Use `--xc-surface-card`, `--xc-border-card`, `--xc-shadow-sm`, and XC spacing tokens for zone containers. Keep all loops, field branching, emitted payload, model updates, values, slider ranges, and first-calculation lock logic unchanged.

Replace all direct rgba control surfaces and borders in this component with Task 1 tokens or existing XC semantic tokens. Preserve control dimensions and disabled styles. Keep primary button gradient behavior and secondary button semantics.

- [ ] **Step 4: Implement elevated dialog sections**

In `AdvancedParamDialog.vue`, add `ir-advanced__section-card` to each existing `.ir-advanced__section`. Change the dialog root to `--xc-surface-raised`, `--xc-border-card`, and `--xc-shadow-raised`; change each section card to `--xc-surface-card` and tokenized border/spacing. Preserve the modal mask interaction, metadata-defined select rendering, slider ranges, read-only behavior, delta directions, `save` payload, and close behavior.

- [ ] **Step 5: Run parameter behavior tests**

Run: `pnpm vitest run tests/param-adjust-panel.spec.js tests/advanced-param-dialog.spec.js tests/param-adjust-logic.spec.js tests/param-adjust-recalculate.spec.js`

Expected: PASS.

## Task 7: Full regression, build, and visual flow verification

**Files:**
- Modify: only test files whose assertions are proven stale solely due to visual structure changes.
- Test: `tests/*.spec.js`

**Interfaces:**
- Consumes: Tasks 1-6.
- Produces: verified visual upgrade with no observed behavior regression.

- [ ] **Step 1: Run all frontend tests**

Run: `pnpm test`

Expected: all Vitest suites PASS. If a test fails, identify whether it asserts changed visual structure or an actual behavior regression. Only update stale visual assertions; fix behavioral regressions in the component that caused them.

- [ ] **Step 2: Run the production build**

Run: `pnpm build`

Expected: exit code 0 with production assets emitted to `dist/`.

- [ ] **Step 3: Run the app for UI verification**

Use the repository’s app-running workflow to start the Vite server. Verify at normal desktop width and a narrow viewport:

1. Welcome state keeps title, light orb, three example chips, input, and send action.
2. Existing completed or mocked calculation result renders state head, three report modules, five KPIs, highlighted project IRR, both charts, and version summary wording.
3. Version selection still scrolls to the selected result and highlights it.
4. Inline parameter controls open, retain metadata-driven field behavior, and advanced dialog saves a draft without independently creating a task.
5. No horizontal page overflow occurs at the narrow viewport.

- [ ] **Step 4: Record verification outcome in the task handoff**

Report exact `pnpm test` and `pnpm build` outcomes, the viewport sizes checked, and any test assertions updated because they were static visual assertions. Do not claim visual verification passed unless the app was actually exercised.

## Plan Self-Review

- **Spec coverage:** Task 1 covers derived XC tokens; Task 2 covers near-black atmospheric shell, 64px top bar, rail, and history panel; Task 3 covers responsive shared content width and welcome state; Task 4 covers three result modules, enlarged KPI hierarchy, project IRR focus, and version wording; Task 5 covers chart cards without contract changes; Task 6 covers inline and modal parameter cardification; Task 7 covers behavior, build, viewport, and flow verification.
- **No behavior drift:** Every implementation task explicitly preserves data, emits, store/API paths, calculation flow, chart semantics, and parameter metadata logic.
- **Placeholder scan:** No unresolved design or implementation placeholders remain. Commands use pnpm and no Git write step is included.
- **Name consistency:** Produced classes are used consistently: `ir-report-module`, `ir-fin__kpi--signature`, `ir-result__head--complete`, `ir-chart--report`, `ir-adjust__zone-card`, and `ir-advanced__section-card`.
