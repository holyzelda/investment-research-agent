# Report Data Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the frozen calculation result contract so the report can render all non-AI template data and charts.

**Architecture:** New values remain owned by the calculation domain: regional cost fields extend `BasicInfo`, ROI extends `FinancialMetrics`, and input-boundary values form `BoundaryParams`. The report module consumes only frozen result/data snapshots. The Vue report route renders the immutable payload and prints to PDF via browser print CSS.

**Tech Stack:** FastAPI, async SQLAlchemy, Python dataclasses, pytest, Vue 3, ECharts, Element Plus.

## Global Constraints

- Work directly on current `main`; do not create a worktree or dispatch subagents.
- Do not run Git write operations.
- Feishu is the only calculator; only read output through `API_OUTPUT` and permitted `画图数据` ranges.
- API responses use `{code, msg, data}` and validation uses HTTP 400.
- Run Python only through `.venv/Scripts/python.exe`; run pytest with `sys.stdout = sys.stderr`.

---

### Task 1: Extend calculation-owned report fields

- [ ] Write focused mapper/view tests for the seven `API_OUTPUT` values and Feishu error strings.
- [ ] Verify the tests fail before implementation.
- [ ] Add `BasicInfo` cost detail fields, `FinancialMetrics.total_investment_roi`, `BoundaryParams`, mapper normalization, and camelCase result view fields.
- [ ] Run the focused mapper suite until green.

### Task 2: Freeze annual revenue and build report payload

- [ ] Write failing source-freezer and report-builder tests for chart revenue row and template-facing sections.
- [ ] Extend the permitted `画图数据` read range/mapping and deterministic report payload.
- [ ] Run focused report/calculation tests until green.

### Task 3: Render report preview and export PDF

- [ ] Add tests for report data loading and route behavior where project patterns support them.
- [ ] Create Vue report preview sections, ECharts chart components, print CSS and conversation progress/card integration.
- [ ] Run frontend checks and manually validate desktop/print layout.

### Task 4: Verify the feature

- [ ] Run the targeted backend suite, frontend build/tests, and inspect the working tree.
- [ ] Report only verified results; do not commit.
