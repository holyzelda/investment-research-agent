# 测算版本差异与项目档案摘要 Implementation Plan

> **For agentic workers:** Execute this plan task-by-task in the current workspace with TDD. Do not run Git commands unless the user explicitly requests them.

**Goal:** Make every calculation version distinguishable by showing parameter/source differences and metric deltas in the result card, while keeping the project archive compact and stable.

**Architecture:** Persist calculation-change metadata alongside each frozen input snapshot. Expose it with conversation versions. Add a pure frontend comparison utility for normalized parameter diffs and KPI semantics; keep temporary comparison selection in the Pinia session store. Reuse that utility in the result card and a compact archive summary, with the archive always comparing adjacent versions.

**Tech Stack:** FastAPI/Python, SQLAlchemy JSON snapshots, Vue 3 `<script setup>`, Pinia, Vitest, existing XC design tokens, `@lucide/vue`.

## Global Constraints

- Default result-card comparison is the adjacent previous successful version.
- The result card may compare any earlier successful version; current/future versions are invalid choices.
- Comparison choices persist only during the current page visit and reset after refresh/reopen.
- Archive summaries always use `Vn` versus `Vn-1`; they never follow the result-card temporary choice.
- Main-card parameter changes are grouped as project basics, editable parameters, and advanced parameters.
- User-explicit changes and system-derived changes must be represented separately by backend metadata.
- The archive shows current-version project IRR prominently, but never shows an IRR delta.
- KPI color expresses economic meaning: higher IRR/profit is green, higher payback is red; lower IRR/profit is red, lower payback is green.
- Trend indicators are line-chart arrows from the existing icon library or equivalent accessible SVG path, never Unicode arrows.
- Revenue donut and cashflow charts receive no textual comparison layer.
- Do not execute `git add`, `git commit`, `git reset`, `git checkout`, branch, or worktree operations.

## File Map

- Create: `agent-frontend/src/utils/versionComparison.js` pure diff/group/KPI helper.
- Modify: `agent-backend/app/modules/calculation/application/snapshot_service.py` to persist change metadata.
- Modify: `agent-backend/app/modules/calculation/application/task_service.py` to compute explicit/derived keys and pass them to snapshots.
- Modify: `agent-backend/app/modules/calculation/application/conversation_history_service.py` and related serializers to expose metadata.
- Modify: `agent-frontend/src/store/modules/calculation.js` to retain metadata and session-only comparison selections.
- Modify: `agent-frontend/src/views/home/components/ResultCard.vue` to render comparison control and diff summary.
- Modify: `agent-frontend/src/views/home/components/FinancialBlock.vue` to render metric deltas and semantic colors.
- Modify: `agent-frontend/src/views/home/index.vue` to render compact archive summaries using adjacent-version metadata.
- Modify: `agent-frontend/src/views/home/index.vue` styles only where archive density/summary layout requires it.
- Test: `agent-frontend/tests/version-comparison.spec.js` utility and store-facing behavior.
- Test: `agent-frontend/tests/result-cards.spec.js` result-card comparison states.
- Test: `agent-frontend/tests/financial-block.spec.js` KPI semantics and trend icons.
- Test: `agent-frontend/tests/version-list.spec.js` archive summary and stable adjacent comparison.
- Test: backend calculation snapshot/task/history tests covering change metadata propagation.

---

### Task 1: Define and persist calculation change metadata

**Files:**
- Modify: `agent-backend/app/modules/calculation/application/snapshot_service.py`
- Modify: `agent-backend/app/modules/calculation/application/task_service.py`
- Modify: `agent-backend/app/modules/calculation/application/conversation_history_service.py`
- Modify: `agent-backend/app/modules/calculation/interface/serializers.py` if response serialization is defined there
- Test: existing calculation snapshot/task/history tests

**Interfaces:**
- `SnapshotService.persist_success(..., change_meta: Optional[dict] = None)` stores `changeMeta` inside `InputSnapshotORM.payload`.
- A completed version response exposes `input.changeMeta` with `previousTaskId`, `explicitOverrideKeys`, and `derivedChangedKeys`.

- [ ] **Step 1: Write failing persistence tests**

Add tests proving that a successful recalculation stores explicit override keys separately from derived keys, and that conversation history returns the same metadata on the version entry. Use an input with `operation_years` and `strategy_achievement_rate` explicitly overridden while `spot_charge_avg` changes through dependency recalculation. Assert exact JSON keys and values.

- [ ] **Step 2: Run the focused backend tests and verify RED**

Run from `agent-backend`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/db/test_snapshot_service.py tests/e2e/calculation/test_calc_endpoints.py -q
```

Expected: failures because `changeMeta` is not persisted or returned.

- [ ] **Step 3: Implement metadata construction and persistence**

Track the incoming `param_overrides` keys at task-service boundary. After `assembled.api_input` is finalized, compare it with the previous frozen input and classify changed keys: explicit keys that remain equal to the submitted final value go to `explicitOverrideKeys`; changed non-explicit keys go to `derivedChangedKeys`. Pass `previousTaskId` and the two sorted key arrays to `SnapshotService.persist_success`, and store the object under `payload.changeMeta`.

- [ ] **Step 4: Expose metadata in history and task responses**

When building each conversation version entry, read `input_snapshot.payload.changeMeta` and expose it without altering existing `input.minInput` or `input.apiInput` fields. Preserve backward compatibility by returning an empty `changeMeta` object for old snapshots.

- [ ] **Step 5: Run focused backend tests and verify GREEN**

Re-run the command above. Expected: PASS with no changes to existing result payload shape.

---

### Task 2: Build the pure frontend comparison model

**Files:**
- Create: `agent-frontend/src/utils/versionComparison.js`
- Test: `agent-frontend/tests/version-comparison.spec.js`

**Interfaces:**
- `normalizeComparableValue(value)` returns a stable comparable representation.
- `diffVersionInputs(currentInput, compareInput, meta, paramDict)` returns `{ groups, totalCount, explicitCount, derivedCount }`.
- `getMetricDelta(key, currentValue, compareValue)` returns `{ delta, direction, tone, text, icon: 'up'|'down'|'flat' }`.
- `buildArchiveSummary(currentVersion, previousVersion, paramDict)` returns compact summary data.

- [ ] **Step 1: Write failing utility tests**

Cover: grouped project basics/editable/advanced fields; explicit versus derived source labels; omitted unchanged fields; normalized numeric equality; missing prior values; five KPI directions; flat KPI; archive two-field truncation and total counts; V1 initial state.

- [ ] **Step 2: Run utility tests and verify RED**

Run from `agent-frontend`:

```powershell
npm test -- --run tests/version-comparison.spec.js
```

Expected: module/function-not-found failures.

- [ ] **Step 3: Implement minimal pure comparison helpers**

Use the existing parameter dictionary fields for labels and category classification. Keep all comparison logic outside Vue components. KPI semantics must encode payback inversion explicitly instead of inferring tone from direction.

- [ ] **Step 4: Run utility tests and verify GREEN**

Run the same command. Expected: PASS.

---

### Task 3: Add session-only comparison selection state

**Files:**
- Modify: `agent-frontend/src/store/modules/calculation.js`
- Test: `agent-frontend/tests/version-comparison.spec.js` or a focused store test

**Interfaces:**
- State: `comparisonVersionByVersion: { [currentVersion]: compareVersion }`.
- Action: `selectComparisonVersion(currentVersion, compareVersion)` validates that compare version is earlier and stores it.
- Getter/helper: `comparisonVersionFor(currentVersion)` returns stored choice or adjacent previous version.
- Reset paths clear the map; history load does not hydrate it.

- [ ] **Step 1: Write failing store tests**

Assert V3 defaults to V2, can select V1, returns V1 when revisiting V3 during the same session, and resets to V2 after `resetConversation`/new history open.

- [ ] **Step 2: Run focused store tests and verify RED**

Run:

```powershell
npm test -- --run tests/version-comparison.spec.js
```

Expected: missing state/action/getter failures.

- [ ] **Step 3: Implement state and actions**

Clear `comparisonVersionByVersion` in `resetConversation` and when opening a fresh conversation. Validate against `this.versions` order and ignore self/future selections.

- [ ] **Step 4: Run focused store tests and verify GREEN**

Run the same command. Expected: PASS.

---

### Task 4: Render result-card version comparison

**Files:**
- Modify: `agent-frontend/src/views/home/components/ResultCard.vue`
- Modify: parent message rendering in `agent-frontend/src/views/home/index.vue` if additional version props are required
- Test: `agent-frontend/tests/result-cards.spec.js`

**Interfaces:**
- ResultCard consumes `compareVersion`, `comparisonResult`, and `availableVersions` props, or equivalent parent/store callbacks.
- Emits `compare-version-change` with the selected earlier version.

- [ ] **Step 1: Write failing component tests**

Assert: V3 renders comparison select defaulting to V2; selecting V1 changes the visible comparison label and grouped rows; source badges distinguish active and derived; V1 hides comparison UI; no duplicate version-diff block appears in the parameter adjustment panel.

- [ ] **Step 2: Run result-card tests and verify RED**

Run:

```powershell
npm test -- --run tests/result-cards.spec.js
```

Expected: missing comparison control/diff content failures.

- [ ] **Step 3: Implement result-card comparison UI**

Add a compact comparison select in the banner, a `版本变化` section above the existing basic/financial modules, and source badges. Keep parameter adjustment controls as the only editing surface. Use existing XC tokens and accessible labels.

- [ ] **Step 4: Wire version selection and temporary persistence**

Pass available earlier versions and selected comparison data from the store. On select, update store state and rerender without changing the archive's adjacent comparison summary.

- [ ] **Step 5: Run focused result-card tests and verify GREEN**

Run the same command. Expected: PASS.

---

### Task 5: Render semantic KPI deltas with line arrows

**Files:**
- Modify: `agent-frontend/src/views/home/components/FinancialBlock.vue`
- Test: `agent-frontend/tests/financial-block.spec.js` or the existing result-card financial assertions

**Interfaces:**
- FinancialBlock consumes `comparisonFinancial` and `comparisonVersion` props.
- It renders `data-tone="good|bad|neutral"` and a Lucide-style path for `up|down|flat`.

- [ ] **Step 1: Write failing KPI tests**

Assert higher IRR/profit is green, lower IRR/profit is red, higher payback is red, lower payback is green, flat is neutral with no trend arrow, and delta units use percentage points/years/millions correctly.

- [ ] **Step 2: Run KPI tests and verify RED**

Run:

```powershell
npm test -- --run tests/financial-block.spec.js
```

Expected: missing comparison props and trend markup failures.

- [ ] **Step 3: Implement KPI delta rendering**

Extend the KPI model with semantic metadata and render a line trend icon from `@lucide/vue` if compatible with the existing import convention. Do not use Unicode arrows. Keep the current value as the strongest visual element and place delta text below it.

- [ ] **Step 4: Run KPI tests and verify GREEN**

Run the same command. Expected: PASS.

---

### Task 6: Compact project archive summaries

**Files:**
- Modify: `agent-frontend/src/views/home/index.vue`
- Modify: `agent-frontend/src/store/modules/calculation.js` only if archive summary data is normalized there
- Test: `agent-frontend/tests/version-list.spec.js`

**Interfaces:**
- Archive consumes `buildArchiveSummary(currentVersion, previousVersion, paramDict)`.
- Archive record displays current `projectIrr` prominently and adjacent-version summary only.

- [ ] **Step 1: Write failing archive tests**

Assert V3 shows `较 V2`, source totals, at most two fields per source, current IRR as the largest record value, V1 shows initial state, and selecting a record only navigates/scrolls without changing the result-card comparison selection.

- [ ] **Step 2: Run archive tests and verify RED**

Run:

```powershell
npm test -- --run tests/version-list.spec.js
```

Expected: missing summary content or incorrect archive behavior failures.

- [ ] **Step 3: Implement compact archive markup and styles**

Keep the existing timeline/list interaction. Replace the selected-only expanded metric treatment with a stable compact record layout where IRR remains prominent on every record, and append a maximum two-line summary. Do not add a drawer or compare selector to the rail.

- [ ] **Step 4: Run archive tests and verify GREEN**

Run the same command. Expected: PASS.

---

### Task 7: Full verification and responsive QA

**Files:**
- Modify only files identified by failing checks.
- Test: all frontend and targeted backend test suites.

- [ ] **Step 1: Run all frontend tests**

From `agent-frontend`:

```powershell
npm test
```

Expected: PASS.

- [ ] **Step 2: Run frontend build**

```powershell
npm run build
```

Expected: successful Vite production build.

- [ ] **Step 3: Run targeted backend calculation tests**

From `agent-backend`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/db/test_snapshot_service.py tests/db/test_calc_task_api.py tests/db/test_conversation_history_api.py tests/e2e/calculation/test_calc_endpoints.py -q
```

Expected: PASS.

- [ ] **Step 4: Run Impeccable mechanical detector**

```powershell
& 'C:\Program Files\nodejs\node.exe' 'C:\Users\JDPC0200\.codex\skills\impeccable\scripts\detect.mjs' --json agent-frontend/src/views/home/index.vue agent-frontend/src/views/home/components/ResultCard.vue agent-frontend/src/views/home/components/FinancialBlock.vue
```

Review all findings; resolve unexplained layout, overflow, focus, icon, color, or token issues.

- [ ] **Step 5: Verify responsive states**

Use the existing local frontend dev server/browser workflow to inspect 1280px desktop and 320px/375px/414px/768px widths. Confirm no horizontal scroll, no clipped comparison select, no archive card overlap, no wrapped button labels, and readable KPI delta icons.

- [ ] **Step 6: Inspect final diff without Git mutation**

Run:

```powershell
git diff --check
git status --short
```

Report modified files and verification results. Do not stage or commit.

