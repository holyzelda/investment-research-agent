# Project Information Compact Strip Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the inline parameter panel’s project-information cards denser and more authoritative without changing parameter behavior.

**Architecture:** This is a CSS-only refinement inside `ParamAdjustPanel.vue`. It preserves the existing dictionary-driven template, V1/V2 locking, station selector, number input bindings, responsive wrap rule, and recalculation payload; only the project information card geometry and text hierarchy change.

**Tech Stack:** Vue 3 scoped CSS, XC CSS custom properties, Vitest, Vue Test Utils.

## Global Constraints

- Do not run `git add`, `git commit`, `git push`, or any Git write operation.
- Do not use Spec-Superflow or modify its artifacts.
- Do not change parameter metadata, parameter ordering, field visibility, locking, control behavior, emitted payloads, or recalculation logic.
- Use existing XC tokens and no new inline colors.
- Preserve the existing small-screen two-column wrapping behavior.

---

## File Structure

| File | Responsibility |
|---|---|
| `src/views/home/components/ParamAdjustPanel.vue` | Own compact project-information card spacing and text hierarchy while preserving the existing template behavior. |
| `tests/param-adjust-panel.spec.js` | Preserve panel behavior and assert the project-information card marker remains present after expansion. |

### Task 1: Compact the Project Information Cards

**Files:**
- Modify: `src/views/home/components/ParamAdjustPanel.vue:259-273`
- Modify: `tests/param-adjust-panel.spec.js:22-35`

**Interfaces:**
- Consumes: existing `.ir-adjust__row--cards`, `.ir-adjust__info-card`, `.ir-adjust__label`, `.ir-adjust__ro`, and `.ir-adjust__number` elements; existing `v-model.number` bindings and field branches.
- Produces: 56px-high compact project information cards with 12px labels, 16px read-only values, and 18px editable numeric values.

- [ ] **Step 1: Extend the panel structure test**

In the existing `default collapsed; expanding renders zones` test, retain the existing assertions and add:

```js
expect(wrapper.findAll('.ir-adjust__info-card').length).toBeGreaterThan(0)
```

- [ ] **Step 2: Run the focused test before changing styles**

Run: `pnpm vitest run tests/param-adjust-panel.spec.js -t "default collapsed"`

Expected: PASS. The assertion verifies the stable project information card marker before the CSS-only refinement.

- [ ] **Step 3: Apply the compact-strip CSS**

Replace the project information card styling with the following declarations while retaining the existing narrow-screen media rule and all template code:

```css
.ir-adjust__row--cards { flex-wrap: nowrap; justify-content: stretch; gap: var(--xc-space-3); }
.ir-adjust__info-card {
  min-height: 56px;
  justify-content: center;
  padding: var(--xc-space-2) var(--xc-space-4);
  border: 0;
  border-left: 2px solid var(--xc-border-accent);
  border-radius: 0 var(--xc-radius-sm) var(--xc-radius-sm) 0;
  background: transparent;
}
.ir-adjust__info-card .ir-adjust__number {
  width: 64px;
  max-width: none;
  padding: 0;
  border-color: transparent;
  border-radius: 0;
  background: transparent;
  color: var(--xc-text-strong);
  font-family: var(--xc-font-num);
  font-size: var(--xc-fs-lg);
  font-weight: var(--xc-fw-semi);
  text-align: left;
}
.ir-adjust__info-card .ir-adjust__ro {
  font-size: var(--xc-fs-md);
  font-weight: var(--xc-fw-semi);
  color: var(--xc-text-strong);
}
.ir-adjust__info-card .ir-adjust__label { font-size: var(--xc-fs-2xs); }
```

Keep the existing focus rule that applies an accent bottom border to editable number inputs.

- [ ] **Step 4: Run focused panel behavior tests**

Run: `pnpm vitest run tests/param-adjust-panel.spec.js`

Expected: PASS, including V1 locking, V2 editable capacity/power, advanced draft merge, and recalculation payload assertions.

- [ ] **Step 5: Run the related regression tests**

Run: `pnpm vitest run tests/param-adjust-panel.spec.js tests/param-adjust-logic.spec.js tests/param-adjust-recalculate.spec.js`

Expected: all tests PASS.

## Plan Self-Review

- **Spec coverage:** The task retains all field ordering, selector/input behavior, V1/V2 locks, metadata-driven rendering, and narrow-screen wrapping while applying the specified 56px height and text hierarchy.
- **No behavior drift:** The plan modifies scoped CSS only; template bindings and script logic are untouched.
- **Placeholder scan:** No unresolved implementation steps or ambiguous style values remain.
