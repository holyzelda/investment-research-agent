# 首次结果项目参数可编辑 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让首次测算结果（V1）的节点、储能装机功率和装机容量可编辑，同时保持会话内省份永久只读。

**Architecture:** 前端继续通过 `ParamAdjustPanel` 的现有 `localValues` 和 `recalculate` 事件提交 `basics`。将纯函数 `isFieldLocked` 收敛为只依据参数字典的 `control: 'fixed'` 判定，取消以版本和项目定义分区整体锁定的规则；组件自然据此将节点渲染为下拉框、功率和容量渲染为数字输入框。同步修订权威 PRD 与 active spec，避免实现、测试和验收规则不一致。

**Tech Stack:** Vue 3 `<script setup>`、Vitest、@vue/test-utils、Markdown spec-superflow 制品。

## Global Constraints

- 项目内省份在所有版本中只读；变更省份必须新建会话。
- V1 起节点、`power_mw`、`capacity_mwh` 可编辑；点击重新测算创建新版本，不覆盖历史版本。
- 不改变 `basics: { node_name, capacity_mwh, power_mw }` 与 `param_overrides` 的既有接口契约。
- 后端已有的节点、容量、功率或日均循环变化时刷新现货价格的逻辑不改动。
- 前端仅用 npm；测试使用 Vitest。
- 不执行 `git add`、`git commit`、`git push` 或其他 Git 写操作。

---

## File Structure

- Modify: `D:/0_工作/2026/投研智能体/docs/prd/PRD-001.md` — 权威 US-1.3 的首次可调性规则和验收场景。
- Modify: `changes/PRD-001-login-calc-mainflow/specs/calc-parameter-adjustment/spec.md` — active spec 的锁项规则和场景。
- Modify: `changes/PRD-001-login-calc-mainflow/execution-contract.md` — active execution contract 的批次验收约束。
- Modify: `changes/PRD-001-login-calc-mainflow/tasks.md` — Batch 5 的锁项测试/实施描述。
- Modify: `src/utils/paramAdjust.js` — 仅保留字典固定项的锁定判定。
- Modify: `tests/param-adjust-logic.spec.js` — 测试锁项纯函数在 V1/V2 的新规则。
- Modify: `tests/param-adjust-panel.spec.js` — 验证 V1 控件可编辑及提交的基础字段。

### Task 1: Update the authoritative requirement and active change contract

**Files:**
- Modify: `D:/0_工作/2026/投研智能体/docs/prd/PRD-001.md:261-275`
- Modify: `changes/PRD-001-login-calc-mainflow/specs/calc-parameter-adjustment/spec.md:18-42`
- Modify: `changes/PRD-001-login-calc-mainflow/execution-contract.md:46,88,125`
- Modify: `changes/PRD-001-login-calc-mainflow/tasks.md:230`

**Interfaces:**
- Consumes: The approved rule: V1 and later versions lock `province` only; `node_name`, `power_mw`, and `capacity_mwh` are editable.
- Produces: One consistent business rule for frontend logic and acceptance tests.

- [ ] **Step 1: Update the PRD US-1.3 business rule and acceptance scenarios**

Replace the V1/V2 lock-rule bullets at `PRD-001.md:261-263` with:

```markdown
- **所有测算版本**：省份 🔒 锁定只读；节点、功率、容量可修改。
```

Replace the first acceptance scenario at `PRD-001.md:269-275` with:

```markdown
*   **场景1: 项目参数编辑**
    *   **GIVEN** 首次测算结果已出
    *   **WHEN** 展开调整参数
    *   **THEN** 省份为只读；节点、功率、容量可编辑，其余可调参数按 G 列可编辑
*   **场景2: 修改项目参数并重算**
    *   **WHEN** 用户改节点或功率并点"重新测算"
    *   **THEN** 生成新版本 V2，旧版本 V1 保留，现货价格按变更后的节点/功率/容量重算
```

- [ ] **Step 2: Align the active spec and execution artifacts**

In `spec.md`, replace wording that describes “首次锁定区” or says V1 locks node/capacity/power with language that explicitly states:

```markdown
省份在所有版本只读；节点、功率、容量在首次结果及后续结果均可编辑。
```

In `execution-contract.md`, replace all three “首次节点/容量/功率锁定，二次起解锁” statements with:

```markdown
省份会话内永久锁定（后端校验，改省需新建会话）；节点、容量、功率在所有版本可编辑。
```

In `tasks.md:230`, replace the Batch 5 lock-item test requirement with:

```markdown
省份在所有版本只读；节点/功率/容量在首次及后续版本均可编辑；项目运营期固定15年、换电成本固定0、贷款年限不展示。
```

- [ ] **Step 3: Review the edited requirements for semantic consistency**

Confirm all four files now agree on these points:

1. `province` is not editable in any version.
2. `node_name`/`power_mw`/`capacity_mwh` are editable in V1 and later.
3. Recalculation creates a later version and retains older versions.
4. No statement still distinguishes V1 versus V2 for node, capacity, or power editability.

Expected: No remaining active-spec assertion describes V1 node, capacity, or power as read-only.

### Task 2: Replace the version-wide project-field lock with dictionary-based locking

**Files:**
- Modify: `src/utils/paramAdjust.js:51-57`
- Test: `tests/param-adjust-logic.spec.js:87-115`

**Interfaces:**
- Consumes: `isFieldLocked(spec, options)` from `ParamAdjustPanel.vue`.
- Produces: `isFieldLocked(spec, options): boolean`, which returns `true` exactly when `spec.control === 'fixed'`. It keeps the second argument for current caller compatibility but does not need it to determine the result.

- [ ] **Step 1: Rewrite the failing V1/V2 lock-rule test**

Replace the describe title and the node/capacity assertion in `tests/param-adjust-logic.spec.js` with:

```js
describe('paramAdjust: 锁项规则（仅字典固定项锁定）', () => {
  it('省份 control=fixed 时始终锁定，不受版本影响', () => {
    const province = PARAM_DICT.find((p) => p.id === 'province')
    expect(isFieldLocked(province, { firstCalc: true })).toBe(true)
    expect(isFieldLocked(province, { firstCalc: false })).toBe(true)
  })

  it('运营期 select 可编辑，换电成本仍固定', () => {
    const years = PARAM_DICT.find((p) => p.id === 'operation_years')
    const battery = PARAM_DICT.find((p) => p.id === 'battery_replace_cost')
    expect(isFieldLocked(years, { firstCalc: true })).toBe(false)
    expect(isFieldLocked(years, { firstCalc: false })).toBe(false)
    expect(isFieldLocked(battery, { firstCalc: true })).toBe(true)
    expect(isFieldLocked(battery, { firstCalc: false })).toBe(true)
  })

  it('节点/容量/功率在首次及后续结果均可编辑', () => {
    const node = PARAM_DICT.find((p) => p.id === 'node_name')
    const capacity = PARAM_DICT.find((p) => p.id === 'capacity_mwh')
    const power = PARAM_DICT.find((p) => p.id === 'power_mw')
    for (const firstCalc of [true, false]) {
      expect(isFieldLocked(node, { firstCalc })).toBe(false)
      expect(isFieldLocked(capacity, { firstCalc })).toBe(false)
      expect(isFieldLocked(power, { firstCalc })).toBe(false)
    }
  })

  it('金融/收益/成本边界的可调参数不受版本限制', () => {
    const epc = PARAM_DICT.find((p) => p.id === 'epc_unit_price')
    expect(isFieldLocked(epc, { firstCalc: true })).toBe(false)
    expect(isFieldLocked(epc, { firstCalc: false })).toBe(false)
  })
})
```

- [ ] **Step 2: Run the focused test and confirm it fails**

Run:

```bash
npm exec vitest -- run tests/param-adjust-logic.spec.js
```

Expected: FAIL at the V1 expectations for node, capacity, and power because the current function locks the whole `project_definition` zone when `firstCalc` is true.

- [ ] **Step 3: Implement the minimal lock-rule change**

Replace `isFieldLocked` in `src/utils/paramAdjust.js` with:

```js
// 仅参数字典声明为 fixed 的字段锁定；省份等固定字段保持只读，
// 节点、容量和功率在所有版本均可编辑。
export function isFieldLocked(spec) {
  return spec.control === 'fixed'
}
```

Do not modify `groupByZone`, `buildOverrides`, `dynamicRange`, or numeric rounding helpers.

- [ ] **Step 4: Run the focused test and confirm it passes**

Run:

```bash
npm exec vitest -- run tests/param-adjust-logic.spec.js
```

Expected: PASS; fixed fields remain locked and V1/V2 project fields with non-fixed controls are unlocked.

### Task 3: Verify V1 controls and recalculation payload in the rendered component

**Files:**
- Modify: `tests/param-adjust-panel.spec.js:38-61,154-168`
- Modify: `src/views/home/components/ParamAdjustPanel.vue:131,195` only if removal of now-unused `firstCalc` is required by lint/style checks.

**Interfaces:**
- Consumes: `isFieldLocked(spec)` from `src/utils/paramAdjust.js`; existing props `paramDict`, `seedInput`, `stationOptions`, and `version`.
- Produces: V1 DOM where province uses `.ir-adjust__ro`, node uses `.ir-adjust__select` when stations exist, and power/capacity use `.ir-adjust__number`; the existing `recalculate` event carries updated `basics`.

- [ ] **Step 1: Replace the obsolete V1 rendering test with an editable-controls test**

Replace the test at `tests/param-adjust-panel.spec.js:38-49` with:

```js
it('V1 中省份只读，节点/容量/功率为可编辑控件', async () => {
  const wrapper = mount(ParamAdjustPanel, {
    props: {
      paramDict: PARAM_DICT,
      switches: { switch_spot: 1 },
      seedInput: SEED,
      stationOptions: ['祥泰站', '新节点'],
      version: 'V1',
    },
  })
  await wrapper.find('.ir-adjust__toggle').trigger('click')

  const roTexts = wrapper.findAll('.ir-adjust__ro').map((n) => n.text())
  expect(roTexts.some((t) => t.includes('甘肃'))).toBe(true)
  expect(wrapper.find('.ir-adjust__select').exists()).toBe(true)

  const projectFields = wrapper.findAll('.ir-adjust__info-card')
  const capacityField = projectFields.find((field) => field.text().includes('装机容量'))
  const powerField = projectFields.find((field) => field.text().includes('储能装机功率'))
  expect(capacityField?.find('input.ir-adjust__number').exists()).toBe(true)
  expect(powerField?.find('input.ir-adjust__number').exists()).toBe(true)
})
```

Replace the V2-specific test at `tests/param-adjust-panel.spec.js:51-61` with a compact regression test that verifies V2 remains editable:

```js
it('V2 中省份仍只读，节点/容量/功率仍可编辑', async () => {
  const wrapper = mount(ParamAdjustPanel, {
    props: {
      paramDict: PARAM_DICT,
      switches: { switch_spot: 1 },
      seedInput: SEED,
      stationOptions: ['祥泰站'],
      version: 'V2',
    },
  })
  await wrapper.find('.ir-adjust__toggle').trigger('click')

  expect(wrapper.findAll('.ir-adjust__ro').some((node) => node.text().includes('甘肃'))).toBe(true)
  expect(wrapper.find('.ir-adjust__select').exists()).toBe(true)
  expect(wrapper.findAll('.ir-adjust__info-card input.ir-adjust__number')).toHaveLength(2)
})
```

- [ ] **Step 2: Add a V1 submission test for edited project values**

Add this test after the existing `提交时携带面板当前完整值作为 overrides 与基础字段` test:

```js
it('V1 提交时携带用户修改后的节点、容量与功率', async () => {
  const wrapper = mount(ParamAdjustPanel, {
    props: {
      paramDict: PARAM_DICT,
      switches: { switch_spot: 1 },
      seedInput: SEED,
      stationOptions: ['祥泰站', '新节点'],
      version: 'V1',
    },
  })
  await wrapper.find('.ir-adjust__toggle').trigger('click')

  await wrapper.find('.ir-adjust__select').setValue('新节点')
  const projectInputs = wrapper.findAll('.ir-adjust__info-card input.ir-adjust__number')
  await projectInputs[0].setValue(1000)
  await projectInputs[1].setValue(250)
  await wrapper.find('.ir-adjust__submit').trigger('click')

  expect(wrapper.emitted('recalculate')[0][0].basics).toEqual({
    node_name: '新节点',
    capacity_mwh: 1000,
    power_mw: 250,
  })
})
```

- [ ] **Step 3: Run the component test and confirm it fails before the logic change is present**

Run:

```bash
npm exec vitest -- run tests/param-adjust-panel.spec.js
```

Expected: On the pre-change implementation, V1 does not render the node selector or number inputs because `isFieldLocked` reports the whole project-definition zone as locked.

- [ ] **Step 4: Apply the Task 2 logic change and keep the component integration minimal**

After Task 2, rerun this test. If `firstCalc` becomes unused in `ParamAdjustPanel.vue`, remove exactly these declarations:

```js
const firstCalc = computed(() => props.version === 'V1')
```

and replace:

```js
function isLocked(spec) { return isFieldLocked(spec, { firstCalc: firstCalc.value }) }
```

with:

```js
function isLocked(spec) { return isFieldLocked(spec) }
```

Keep the `version` prop because callers and existing component fixtures supply it; do not change request payload construction.

- [ ] **Step 5: Run focused frontend regression tests**

Run:

```bash
npm exec vitest -- run tests/param-adjust-logic.spec.js tests/param-adjust-panel.spec.js tests/param-adjust-recalculate.spec.js
```

Expected: PASS. This demonstrates the changed lock rule, V1 editable rendered controls, V1 modified `basics` payload, and existing recalculation behavior together.

- [ ] **Step 6: Run the complete frontend test suite**

Run:

```bash
npm test
```

Expected: PASS with no failures. If a failure refers to the former V1-lock behavior, update only the expectation to the approved policy; do not change unrelated behavior.

## Plan Self-Review

- **Spec coverage:** Task 1 synchronizes the authoritative PRD plus all active spec-superflow rules; Task 2 changes the isolated lock decision and verifies both V1/V2 behavior; Task 3 verifies actual V1 DOM editability, updated `basics` payload, historical V2 behavior, and full test-suite compatibility.
- **Placeholder scan:** No TBD/TODO placeholders or undefined test actions remain.
- **Type consistency:** `isFieldLocked(spec)` returns a boolean; component props and emitted `{ overrides, basics }` retain their existing names and shapes.
