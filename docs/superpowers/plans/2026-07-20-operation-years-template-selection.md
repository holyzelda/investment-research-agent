# 20 年运营期飞书模板选择 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 支持用户以已有 `operation_years` 参数在 15 年与 20 年飞书底稿间切换，并让每个版本的冻结运营期可追溯。

**Architecture:** `operation_years` 保持在参数字典、API 入参与 `input_snapshot` 中，但不再写入飞书接口区。后端任务服务在组装并应用覆盖后，从冻结运营期显式选择飞书模板 token；网关只负责用该 token 复制副本。前端使用参数字典驱动高级参数下拉与最小化文本提取，仍通过既有 `param_overrides` 重算链路提交。

**Tech Stack:** Python 3.13、FastAPI、Pydantic、SQLAlchemy 异步测试、httpx、pytest；Vue 3、Pinia、Vitest、Vue Test Utils；飞书 Drive/Sheets API。

## Global Constraints

- 活跃 spec-superflow 变更是 `changes/PRD-001-login-calc-mainflow`；实施前必须完成该变更的 delta specs、合同刷新、DP-3 批准和当前执行计划，不得绕过状态机。
- 15 年模板配置字段必须为 `feishu.template_token_15_years`；20 年字段必须为 `feishu.template_token_20_years`，其值为 `exampleToken000000000000048`。
- `operation_years` 仅允许整数 `15` 或 `20`；缺省按参数字典默认 `15` 处理；非法值必须在复制飞书副本前失败，不得回退。
- `operation_years` 必须保留在最终 `api_input`、任务响应和 `input_snapshot`，但绝不写入 `API_INPUT`（原 `API_INPUT!B11` 不再使用）。
- 15 年或 20 年的版本可在同一 `conversation_id` 中混用；运营期不影响省份锁定、现货依赖比较或收益结构重算。
- 飞书只允许读写 `API_INPUT`、`API_OUTPUT`、`API_META` 和 `画图数据`；不直接读写模型单元格。
- 不增加大模型抽取、其他运营期、第二条请求链路、第二套飞书客户端或模板回退逻辑。
- Python 测试使用 `.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main([...]))"` 包装；前端统一使用 `pnpm`。
- 不执行 `git add`、`git commit`、`git push` 或其他 git 写操作；提交步骤由用户手动完成。

---

## File Structure

| Path | Responsibility |
| --- | --- |
| `changes/PRD-001-login-calc-mainflow/specs/calc-parameter-dictionary/spec.md` | 追加运营期为模板选择元数据、非法值和非 API_INPUT 写入的需求。 |
| `changes/PRD-001-login-calc-mainflow/specs/calc-execution-engine/spec.md` | 追加按冻结运营期复制对应模板、重试复用副本和快照追溯的需求。 |
| `changes/PRD-001-login-calc-mainflow/specs/calc-conversation/spec.md` | 追加临时 15/20 年文本提取及默认 15 年需求。 |
| `changes/PRD-001-login-calc-mainflow/specs/calc-parameter-adjustment/spec.md` | 将运营期从固定 15 年修订为高级参数下拉可选 15 / 20 年。 |
| `changes/PRD-001-login-calc-mainflow/execution-contract.md` | 扩展范围、任务批次、测试义务和 DP-3 批准边界。 |
| `agent-backend/app/core/config/settings.py` | 定义和加载 15 年 / 20 年对称飞书模板配置。 |
| `agent-backend/configs/application.yml` | 将既有 15 年 token 迁移到新字段并配置 20 年 token。 |
| `agent-backend/app/modules/calculation/infrastructure/data/param_dict.json` | 将运营期改为 15/20 枚举元数据，移除运行时 API_INPUT 单元格映射。 |
| `agent-backend/app/modules/calculation/domain/param_dictionary.py` | 解析并承载参数枚举选项元数据。 |
| `agent-backend/app/modules/calculation/application/param_assembler.py` | 对运营期覆盖做白名单与 15/20 校验，确保冻结值保留。 |
| `agent-backend/app/modules/calculation/application/task_service.py` | 在首次飞书复制前由冻结运营期选择模板 token。 |
| `agent-backend/app/modules/calculation/domain/ports.py` | 将 `FeishuGateway.copy_template` 端口改为接收本次模板 token。 |
| `agent-backend/app/modules/calculation/infrastructure/feishu_client.py` | 同步 mock 网关的新复制端口签名并记录调用 token，供任务测试断言。 |
| `agent-backend/app/modules/calculation/infrastructure/feishu_http_client.py` | 用调用方传入的 token 作为 Drive copy 的源，并跳过 `operation_years` 写入。 |
| `agent-backend/tests/unit/calculation/test_param_dictionary.py` | 覆盖运营期枚举元数据和不再映射 API_INPUT。 |
| `agent-backend/tests/integration/calculation/test_param_assembler.py` | 覆盖 15/20 接受、非法运营期拒绝和最终冻结入参。 |
| `agent-backend/tests/integration/calculation/test_task_service_overrides.py` | 覆盖 V1/V2 15/20 模板选择、同会话混用、非法值不复制。 |
| `agent-backend/tests/integration/calculation/test_feishu_http_client.py` | 覆盖 Drive copy 使用传入 token 与 `write_input` 跳过运营期。 |
| `agent-frontend/src/store/modules/calculation.js` | 从首次对话文本提取明确的 15 年 / 20 年表述，并将命中值作为既有覆盖提交。 |
| `agent-frontend/src/views/home/components/AdvancedParamDialog.vue` | 根据参数字典的枚举元数据渲染运营期下拉，并将选中值暂存为高级参数覆盖。 |
| `agent-frontend/src/utils/paramAdjust.js` | 让 `buildOverrides` 收集字典声明的枚举控件值。 |
| `agent-frontend/tests/advanced-param-dialog.spec.js` | 覆盖 15/20 下拉渲染和保存草稿。 |
| `agent-frontend/tests/param-adjust-logic.spec.js` | 覆盖枚举运营期进入重算覆盖。 |
| `agent-frontend/tests/calc-flow.spec.js` | 覆盖文本中的明确运营期提交，以及未提及运营期时不覆盖默认值。 |

### Task 1: Refresh the Spec-Superflow Artifacts and Contract

**Files:**
- Modify: `changes/PRD-001-login-calc-mainflow/specs/calc-parameter-dictionary/spec.md`
- Modify: `changes/PRD-001-login-calc-mainflow/specs/calc-execution-engine/spec.md`
- Modify: `changes/PRD-001-login-calc-mainflow/specs/calc-conversation/spec.md`
- Modify: `changes/PRD-001-login-calc-mainflow/specs/calc-parameter-adjustment/spec.md`
- Modify: `changes/PRD-001-login-calc-mainflow/execution-contract.md`

**Interfaces:**
- Consumes: approved design at `docs/superpowers/specs/2026-07-20-operation-years-template-selection-design.md`.
- Produces: a refreshed contract that names `template_token_15_years`, `template_token_20_years`, `operation_years` validation, no `API_INPUT` write, and test obligations used to obtain DP-3 approval.

- [ ] **Step 1: Add the parameter-dictionary delta requirement**

Append a `MODIFIED Requirements` section to `calc-parameter-dictionary/spec.md` with this requirement and scenarios:

```markdown
### Requirement: 项目运营期作为模板选择参数

The system SHALL 将 `operation_years` 维护为系统内模板选择和版本追溯参数，默认值为 `15`，仅允许整数 `15` 或 `20`。参数字典 SHALL 声明其为可编辑枚举控件，选项为“15年”和“20年”。该字段 SHALL 保留在最终组装入参与快照中，但 SHALL 不映射或写入 `API_INPUT`。

#### Scenario: 缺省采用 15 年
- **WHEN** 请求未提交 `operation_years` 覆盖
- **THEN** 组装入参包含 `operation_years=15`

#### Scenario: 非法运营期被拒绝
- **WHEN** 覆盖值不是整数 15 或 20
- **THEN** 后端在飞书副本复制前返回参数校验错误

#### Scenario: 运营期不写接口区
- **WHEN** 网关写入组装入参
- **THEN** 请求中不包含 `API_INPUT!B11` 的更新范围
```

- [ ] **Step 2: Add execution-engine and conversation delta requirements**

Append requirements that make the task service select `template_token_15_years` for 15 and `template_token_20_years` for 20, pass the chosen token into one copy operation, retain the value in `input_snapshot`, and permit mixed 15/20 versions in one conversation. Append the conversation requirement below:

```markdown
### Requirement: 临时运营期文本提取

The system SHALL 在当前前端规则解析中仅识别明确的 15 年或 20 年运营期表述；未识别时 SHALL 不提交运营期覆盖，后端默认值为 15。该规则是临时实现，不引入模型调用或新的 API 字段。
```

- [ ] **Step 3: Replace the fixed-15-year adjustment rule**

In `calc-parameter-adjustment/spec.md`, replace the sentence `项目运营期本阶段固定 15 年` with a requirement that it appears only in the existing advanced dialog as a `select`, has exactly 15 and 20 options, and contributes `param_overrides.operation_years` when saved. Keep `battery_replace_cost` fixed because that is not in scope.

- [ ] **Step 4: Refresh the execution contract**

Add an execution batch dedicated to the 20-year template selection. Its scope must state all of the following:

```markdown
1. 将既有 `feishu.template_token` 迁移为 `template_token_15_years`，并增加 `template_token_20_years`。
2. `operation_years` 是仅限 15/20 的模板选择参数；最终冻结值决定每次副本的来源。
3. `operation_years` 留在 input snapshot，但不写 `API_INPUT!B11`。
4. 前端仅做明确 15/20 文本提取，并在高级参数中提供 15/20 下拉。
5. 同会话可混合 15 年和 20 年版本；重试复用当前副本。
6. 后端 pytest、前端 Vitest 和 `pnpm build` 是批次完成前的硬验证。
```

Update the contract’s pending DP-3 approval text so it asks for this new delta explicitly.

- [ ] **Step 5: Run spec-superflow artifact checks**

Run:

```bash
npx --yes --package spec-superflow@0.10.0 ssf runtime guard check "D:/1_code/investment-research-agent/changes/PRD-001-login-calc-mainflow" exploring specifying --json
```

Expected: exit code 0 and JSON indicating the transition can proceed; if it fails, stop and resolve the reported artifact inconsistency before editing implementation code.

- [ ] **Step 6: Obtain the required DP-3 contract approval**

Present the refreshed contract scope to the user. Do not edit application code until they explicitly approve the refreshed contract.

- [ ] **Step 7: Record the approval and construct a current execution plan**

After approval, use the spec-superflow contract-builder/build-executor flow to persist DP-3, request execution-mode recommendation, obtain DP-4 mode selection, create the current execution plan, and verify `ssf execution show` reports `current: true`. The first implementation edit is blocked until this succeeds.

- [ ] **Step 8: User-managed commit checkpoint**

Do not run Git commands. Tell the user which changed spec files form this checkpoint and let them commit if desired.

### Task 2: Add Backend Configuration and Parameter Metadata

**Files:**
- Modify: `agent-backend/app/core/config/settings.py:98-120,209-225`
- Modify: `agent-backend/configs/application.yml:37-55`
- Modify: `agent-backend/app/modules/calculation/domain/param_dictionary.py:12-45`
- Modify: `agent-backend/app/modules/calculation/infrastructure/data/param_dict.json:54`
- Test: `agent-backend/tests/unit/calculation/test_param_dictionary.py`

**Interfaces:**
- Consumes: `FeishuConfig.template_token_15_years: str`, `FeishuConfig.template_token_20_years: str`; `ParamSpec.options: list[dict[str, object]] | None`.
- Produces: parameter metadata where `operation_years` has `control="select"`, `options=[{"value":15,"label":"15年"},{"value":20,"label":"20年"}]`, `api_cell=null`, and default `15`.

- [ ] **Step 1: Write failing parameter-dictionary tests**

Add assertions to `test_param_dictionary.py`:

```python
operation_years = dictionary.get("operation_years")
assert operation_years.control == "select"
assert operation_years.options == [
    {"value": 15, "label": "15年"},
    {"value": 20, "label": "20年"},
]
assert operation_years.api_cell is None
assert dictionary.defaults()["operation_years"] == 15
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/calculation/test_param_dictionary.py', '-q']))"
```

Expected: FAIL because `ParamSpec` has no `options` field and the JSON still has `control="fixed"` plus `api_cell`.

- [ ] **Step 3: Add the metadata model and JSON contract**

Change `ParamSpec` and `from_dict`:

```python
options: Optional[list[dict]] = None

# in from_dict(...)
options=d.get("options"),
```

Replace the `operation_years` record with:

```json
{
  "id": "operation_years",
  "cn": "项目运营期",
  "category": "运营期与换电",
  "source": "default",
  "model_cell": null,
  "f": 1,
  "g": 1,
  "writable": true,
  "direction": "input",
  "api_cell": null,
  "default": 15,
  "unit": "年",
  "dtype": "int",
  "zone": "financial_boundary",
  "control": "select",
  "options": [{"value": 15, "label": "15年"}, {"value": 20, "label": "20年"}],
  "note": "仅用于选择15年或20年飞书模板；不写入API_INPUT"
}
```

- [ ] **Step 4: Write failing configuration tests**

Add a focused test to the existing settings test module, or create `agent-backend/tests/unit/core/test_settings.py` if absent:

```python
def test_feishu_config_exposes_two_operation_year_template_tokens():
    cfg = FeishuConfig(template_token_15_years="t15", template_token_20_years="t20")
    assert cfg.template_token_15_years == "t15"
    assert cfg.template_token_20_years == "t20"
```

- [ ] **Step 5: Implement symmetric configuration names**

Replace the existing single field and loader entry:

```python
class FeishuConfig(BaseModel):
    # ... existing fields ...
    template_token_15_years: str = ""
    template_token_20_years: str = ""
```

```python
template_token_15_years=os.getenv(
    "IR_FEISHU_TEMPLATE_TOKEN_15_YEARS",
    _nested(y, ["feishu", "template_token_15_years"], ""),
),
template_token_20_years=os.getenv(
    "IR_FEISHU_TEMPLATE_TOKEN_20_YEARS",
    _nested(y, ["feishu", "template_token_20_years"], ""),
),
```

In `application.yml`, rename the existing 15-year key and add:

```yaml
template_token_15_years: "exampleToken000000000000047"
template_token_20_years: "exampleToken000000000000048"
```

- [ ] **Step 6: Run focused backend unit tests**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/calculation/test_param_dictionary.py', 'tests/unit/core/test_settings.py', '-q']))"
```

Expected: PASS.

- [ ] **Step 7: User-managed commit checkpoint**

Do not run Git commands. Report the configuration, metadata, and test files that are ready for user review or commit.

### Task 3: Enforce Backend Selection, Validation, and No-Write Behavior

**Files:**
- Modify: `agent-backend/app/modules/calculation/application/param_assembler.py:81-144,174-182`
- Modify: `agent-backend/app/modules/calculation/application/task_service.py:90-120`
- Modify: `agent-backend/app/modules/calculation/domain/ports.py:46-51`
- Modify: `agent-backend/app/modules/calculation/infrastructure/feishu_client.py`
- Modify: `agent-backend/app/modules/calculation/infrastructure/feishu_http_client.py:179-185,187-198`
- Test: `agent-backend/tests/integration/calculation/test_param_assembler.py`
- Test: `agent-backend/tests/integration/calculation/test_task_service_overrides.py`
- Test: `agent-backend/tests/integration/calculation/test_feishu_http_client.py`

**Interfaces:**
- Consumes: `operation_years` default/options from `ParamDictionary`; `FeishuConfig.template_token_15_years`, `FeishuConfig.template_token_20_years`.
- Produces: `CalculationTaskService._template_token_for(api_input: dict) -> str`; `FeishuGateway.copy_template(template_token: str, name: Optional[str] = None) -> str`.

- [ ] **Step 1: Write failing assembler validation tests**

Add tests to `test_param_assembler.py`:

```python
def test_operation_years_override_20_is_frozen_in_api_input():
    assembled = assembler.assemble(BASICS, overrides={"operation_years": 20})
    assert assembled.api_input["operation_years"] == 20

@pytest.mark.parametrize("invalid", [None, 14, 16, 21, "20"])
def test_invalid_operation_years_override_is_rejected(invalid):
    with pytest.raises(ValidationException, match="项目运营期仅支持15年或20年"):
        assembler.assemble(BASICS, overrides={"operation_years": invalid})
```

Use the test module’s existing assembler fixture and imports; the `None` case should be handled as “not an override” only if it comes from an omitted key, so write a separate assertion that omitted overrides retain 15. A submitted `None` is rejected if validation happens at request/override processing.

- [ ] **Step 2: Write failing task-service template-selection tests**

Extend the fake/mock gateway to record `copy_template` arguments, then add:

```python
@pytest.mark.asyncio
async def test_v1_uses_15_year_template_by_default(session_maker):
    gateway = _RecordingGateway(output=sample_output())
    service = _service(_CountingSpot(), gateway=gateway)
    async with session_maker() as session:
        await service.create_and_run(session, user_id="u1", username="U1", basics=_BASICS)
    assert gateway.copy_calls == [("template-15", pytest.any(str))]

@pytest.mark.asyncio
async def test_v2_can_switch_to_20_year_template_in_same_conversation(session_maker):
    gateway = _RecordingGateway(output=sample_output())
    service = _service(_CountingSpot(), gateway=gateway)
    async with session_maker() as session:
        v1 = await service.create_and_run(session, user_id="u1", username="U1", basics=_BASICS)
        v2 = await service.create_and_run(
            session, user_id="u1", username="U1", basics=_BASICS,
            conversation_id=v1["conversationId"], param_overrides={"operation_years": 20},
        )
        assert v2["input"]["operation_years"] == 20
    assert [token for token, _ in gateway.copy_calls] == ["template-15", "template-20"]
```

Construct the service with a test `FeishuConfig` or inject a simple template selector so the test does not read development YAML.

- [ ] **Step 3: Run focused tests and verify failure**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/integration/calculation/test_param_assembler.py', 'tests/integration/calculation/test_task_service_overrides.py', '-q']))"
```

Expected: FAIL because no selector exists and `copy_template` has no template-token argument.

- [ ] **Step 4: Implement strict operational-period validation**

Add a small validation helper to `ParamAssembler` and call it before applying overrides:

```python
_OPERATION_YEARS = {15, 20}

def _validate_operation_years(self, overrides: dict) -> None:
    if "operation_years" not in overrides:
        return
    value = overrides["operation_years"]
    if type(value) is not int or value not in _OPERATION_YEARS:
        raise ValidationException("项目运营期仅支持15年或20年")
```

Keep `operation_years` in the existing g=1 writable input whitelist so valid values are written to `assembled.api_input` and snapshots. Do not add it to any spot or revenue dependency comparison.

- [ ] **Step 5: Implement task-level template selection and new gateway port**

In `CalculationTaskService`, inject `FeishuConfig` through the existing factory construction path and add:

```python
def _template_token_for(self, api_input: dict) -> str:
    years = api_input.get("operation_years", 15)
    if years == 15:
        return self._feishu.template_token_15_years
    if years == 20:
        return self._feishu.template_token_20_years
    raise ValidationException("项目运营期仅支持15年或20年")
```

Select the token after `assemble(...)` and before calling `run_with_retry`, then call:

```python
copy_template=lambda: self._gateway.copy_template(template_token, copy_name)
```

Change the port and every implementation/stub signature to:

```python
async def copy_template(self, template_token: str, name: Optional[str] = None) -> str:
```

The retry lambda remains unchanged, so it copies once and reuses the returned `doc_token` on retry.

- [ ] **Step 6: Write the failing HTTP-client no-write tests**

Add to `test_feishu_http_client.py`:

```python
@pytest.mark.asyncio
async def test_copy_uses_supplied_template_token():
    fake = FakeFeishu()
    gw = _gateway(fake)
    await gw.copy_template("template-20", "宁夏-200/400-20260710091435")
    assert fake.copy_path.endswith("/drive/v1/files/template-20/copy")
    await gw._client.aclose()

@pytest.mark.asyncio
async def test_write_input_skips_operation_years_even_when_frozen_input_contains_it():
    fake = FakeFeishu()
    gw = _gateway(fake)
    await gw.write_input("doc1", {"power_mw": 100, "operation_years": 20})
    written = fake.batch_updates[0]
    assert written == [{"range": "shtI!B2:B2", "values": [[100]]}]
    await gw._client.aclose()
```

Extend `FakeFeishu` to save `request.url.path` for copy requests.

- [ ] **Step 7: Implement HTTP copy source and API_INPUT skip**

Change `HttpFeishuGateway.copy_template` to use the provided token:

```python
async def copy_template(self, template_token: str, name: Optional[str] = None) -> str:
    name = name or f"{self._cfg.copy_name_prefix}-{uuid.uuid4().hex[:8]}"
    body = await self._authed(
        "POST", f"/open-apis/drive/v1/files/{template_token}/copy",
        json={"name": name, "type": "sheet", "folder_token": self._cfg.target_folder_token},
    )
    return body["data"]["file"]["token"]
```

At the start of `write_input`’s loop, add:

```python
if pid == "operation_years":
    continue
```

This explicit guard protects against future metadata changes that accidentally add an `api_cell` for the selection-only field.

- [ ] **Step 8: Run backend focused tests**

Run:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/integration/calculation/test_param_assembler.py', 'tests/integration/calculation/test_task_service_overrides.py', 'tests/integration/calculation/test_feishu_http_client.py', '-q']))"
```

Expected: PASS. The V2 test proves mixed-year versions work and the HTTP test proves the copied source uses the selected template while input writing excludes the operational period.

- [ ] **Step 9: User-managed commit checkpoint**

Do not run Git commands. Report the backend implementation and test files ready for user review or commit.

### Task 4: Add Frontend Extraction and Metadata-Driven Select

**Files:**
- Modify: `agent-frontend/src/store/modules/calculation.js:28-47,158-176`
- Modify: `agent-frontend/src/views/home/components/AdvancedParamDialog.vue:18-52,94-149`
- Modify: `agent-frontend/src/utils/paramAdjust.js:59-68`
- Test: `agent-frontend/tests/calc-flow.spec.js`
- Test: `agent-frontend/tests/advanced-param-dialog.spec.js`
- Test: `agent-frontend/tests/param-adjust-logic.spec.js`

**Interfaces:**
- Consumes: backend parameter metadata `control: "select"` and `options: [{ value: 15, label: "15年" }, { value: 20, label: "20年" }]`.
- Produces: `extractMinInput(text)` returning optional `operation_years`; advanced dialog emits `{ operation_years: 15 | 20 }`; `buildOverrides` returns the selected value when present.

- [ ] **Step 1: Write failing extraction tests**

In `calc-flow.spec.js`, add:

```javascript
import { extractMinInput } from '@/store/modules/calculation'

it.each([
  ['测算甘肃 200MW/800MWh，运营期20年', 20],
  ['按15年测算甘肃 200MW/800MWh', 15],
])('extracts explicit operation years from %s', (text, expected) => {
  expect(extractMinInput(text).operation_years).toBe(expected)
})

it('leaves operation years unset when the text does not specify it', () => {
  expect(extractMinInput('测算甘肃 200MW/800MWh').operation_years).toBeNull()
})
```

Add a store action test that verifies explicit 20 sends `param_overrides: { operation_years: 20 }`, while omitted years do not send `param_overrides`.

- [ ] **Step 2: Write failing advanced-dialog select tests**

Replace the existing fixed-operation-years fixture with:

```javascript
{
  id: 'operation_years', cn: '项目运营期', zone: 'financial_boundary',
  control: 'select', default: 15, unit: '年', g: 1,
  options: [{ value: 15, label: '15年' }, { value: 20, label: '20年' }],
}
```

Add:

```javascript
it('renders only the metadata-provided 15 and 20 year options and saves 20', async () => {
  const wrapper = mount(AdvancedParamDialog, { props: { modelValue: true, paramDict: PARAM_DICT, seedInput: SEED } })
  const select = wrapper.find('select[data-param-id="operation_years"]')
  expect(select.findAll('option').map((option) => option.text())).toEqual(['15年', '20年'])
  await select.setValue('20')
  await wrapper.find('.ir-advanced__save').trigger('click')
  expect(wrapper.emitted('save')[0][0]).toMatchObject({ operation_years: 20 })
})
```

- [ ] **Step 3: Write failing override-collection tests**

Add to `param-adjust-logic.spec.js`:

```javascript
it('includes a metadata-defined select value in recalculation overrides', () => {
  const dict = [{ id: 'operation_years', control: 'select', g: 1, options: [{ value: 15 }, { value: 20 }] }]
  expect(buildOverrides(dict, { operation_years: 20 })).toEqual({ operation_years: 20 })
})
```

- [ ] **Step 4: Run focused frontend tests and verify failure**

Run from `agent-frontend`:

```bash
pnpm vitest run tests/calc-flow.spec.js tests/advanced-param-dialog.spec.js tests/param-adjust-logic.spec.js
```

Expected: FAIL because extraction returns no operational period, the dialog has no select branch, and `buildOverrides` excludes select controls.

- [ ] **Step 5: Implement the temporary explicit-text extractor**

In `extractMinInput`, add before the return:

```javascript
const operationYearsMatch = content.match(/(?:运营期|经营年限|按)\s*(15|20)\s*年|(?:15|20)\s*年\s*(?:运营期|经营年限|测算)/)
const operationYears = operationYearsMatch ? Number(operationYearsMatch[1] || operationYearsMatch[0].match(/15|20/)[0]) : null
```

Return `operation_years: operationYears`. In `sendAndCalculate`, add only for a recognized value:

```javascript
if (input.operation_years !== null) {
  payload.param_overrides = { operation_years: input.operation_years }
}
```

Do not add a new request field or send a default override.

- [ ] **Step 6: Render select controls from metadata and preserve numeric type**

Add a select branch before the numeric editable branch:

```vue
<select
  v-else-if="spec.control === 'select'"
  :data-param-id="spec.id"
  v-model.number="values[spec.id]"
  class="ir-advanced__select"
>
  <option v-for="option in spec.options || []" :key="option.value" :value="option.value">
    {{ option.label }}
  </option>
</select>
```

Update `isEditable` so it returns true for `select`. Update `save()` so a selected `control === 'select'` with `g === 1` is included alongside slider values. Style `.ir-advanced__select` with the existing input height, surface, border, text color, and responsive width; do not introduce a second option list or hard-code 15/20 in the component.

- [ ] **Step 7: Include select controls in full-panel overrides**

Update `buildOverrides`:

```javascript
if (!['slider', 'dynamic_slider', 'select'].includes(spec.control)) continue
if (spec.g !== 1 || !(spec.id in values)) continue
```

This ensures an advanced dialog selection persists when the regular parameter panel emits the merged recalculation request.

- [ ] **Step 8: Run focused frontend tests**

Run:

```bash
pnpm vitest run tests/calc-flow.spec.js tests/advanced-param-dialog.spec.js tests/param-adjust-logic.spec.js
```

Expected: PASS.

- [ ] **Step 9: User-managed commit checkpoint**

Do not run Git commands. Report the frontend implementation and test files ready for user review or commit.

### Task 5: Run Cross-Stack Regression and Perform the Spec Review Gate

**Files:**
- Modify only if failures reveal a scoped defect: files listed in Tasks 2–4.
- Test: `agent-backend/tests/unit/calculation/test_param_dictionary.py`
- Test: `agent-backend/tests/integration/calculation/test_param_assembler.py`
- Test: `agent-backend/tests/integration/calculation/test_task_service_overrides.py`
- Test: `agent-backend/tests/integration/calculation/test_feishu_http_client.py`
- Test: `agent-frontend/tests/calc-flow.spec.js`
- Test: `agent-frontend/tests/advanced-param-dialog.spec.js`
- Test: `agent-frontend/tests/param-adjust-logic.spec.js`

**Interfaces:**
- Consumes: completed implementation tasks and the current spec-superflow execution plan.
- Produces: passing verification evidence and a spec-superflow wave review receipt required before closing or dependent work.

- [ ] **Step 1: Run the backend regression selection**

Run from `agent-backend`:

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/calculation/test_param_dictionary.py', 'tests/integration/calculation/test_param_assembler.py', 'tests/integration/calculation/test_task_service_overrides.py', 'tests/integration/calculation/test_feishu_http_client.py', '-q']))"
```

Expected: PASS with tests covering default 15, explicit 20, invalid rejection before copy, selected Drive source token, no `operation_years` API_INPUT write, and mixed-version snapshots.

- [ ] **Step 2: Run the complete frontend test suite and production build**

Run from `agent-frontend`:

```bash
pnpm test
pnpm build
```

Expected: both commands exit 0. If a test explicitly asserts the retired “operation years never appears” behavior, update that test only where it conflicts with the approved advanced-dialog requirement; preserve the main inline panel’s existing hidden-field behavior.

- [ ] **Step 3: Inspect the final changed paths against the scope fence**

Verify the changed paths are confined to the spec artifacts, configuration, parameter contract, task/gateway path, temporary conversation extraction, advanced-parameter dialog, and targeted tests. Reject unrelated refactors, formula changes, extra model extraction, or non-15/20 options.

- [ ] **Step 4: Request the required spec-superflow wave review**

Use the active change’s code-reviewer route. The review report must check: token selection happens after final overrides, invalid values fail before copy, retries use one copied document, `operation_years` is retained in snapshots but excluded from `API_INPUT`, and 15/20 versions can coexist in one conversation.

- [ ] **Step 5: Write the spec-superflow review receipt**

After a passing review, run the required `ssf execution review` command using the current plan’s wave ID, base SHA, head SHA, review-report path, and `--verdict pass`. Do not start dependent waves or closing work until the receipt exists.

- [ ] **Step 6: User-managed final commit checkpoint**

Do not run Git commands. Summarize implementation, test/build outcomes, spec review receipt, and the exact changed files for the user to inspect and commit.

## Plan Self-Review

- **Spec coverage:** Task 1 updates the active change’s parameter-dictionary, execution-engine, conversation, and parameter-adjustment specifications plus its contract. Task 2 provides the configuration and metadata source of truth. Task 3 covers strict backend validation, template choice, copy token propagation, API_INPUT exclusion, retry preservation, snapshot retention, and mixed versions. Task 4 covers explicit temporary extraction and metadata-driven advanced select. Task 5 runs the required backend/frontend checks and spec-superflow review receipt.
- **Placeholder scan:** No task depends on an undefined feature or leaves a behavior unspecified. Values, field names, file paths, test commands, expected outcomes, and method signatures are explicit.
- **Type consistency:** `operation_years` is an integer throughout; `ParamSpec.options` is parsed from JSON and serialized through the existing dictionary endpoint; `copy_template(template_token, name)` is consistent across port, mock, HTTP implementation, and task service; configuration fields use matching 15/20 names throughout.
