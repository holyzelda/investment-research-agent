# 政策与市场历史研究记录硬删除 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为政策与市场的历史研究记录增加悬停删除入口、二次确认与按当前用户归属的数据库硬删除能力。

**Architecture:** 后端在现有 `interface → application → domain → infrastructure` 边界内增加单条删除链路，以 `record_id + user_id` 作为数据库删除条件并以受影响行数表达删除结果。前端沿用首页会话历史的 Element Plus 确认框模式：组件只发出删除事件，页面负责确认提示，Pinia store 在 API 成功后同步删除列表、详情缓存和当前选中状态。

**Tech Stack:** FastAPI、SQLAlchemy Async、SQLite 测试数据库、Vue 3、Pinia、Element Plus、Vitest、Vue Test Utils、pytest/httpx。

---

## 文件结构

- 修改：`agent-backend/app/modules/policy_market/domain/ports.py`
  - 扩展咨询记录仓储 Protocol，声明按记录 ID 和用户 ID 删除的端口。
- 修改：`agent-backend/app/modules/policy_market/infrastructure/persistence/consultation_repository.py`
  - 执行带用户归属条件的 SQLAlchemy 硬删除。
- 修改：`agent-backend/app/modules/policy_market/application/consultation_service.py`
  - 暴露按当前用户删除咨询记录的应用服务。
- 修改：`agent-backend/app/modules/policy_market/interface/router.py`
  - 新增 DELETE 端点、404 处理、事务提交与统一成功响应。
- 修改：`agent-backend/tests/e2e/policy_market/test_consultation_endpoints.py`
  - 覆盖成功硬删除、数据真实移除和跨用户/不存在记录的 404 隔离。
- 修改：`agent-frontend/src/api/policyMarket.js`
  - 新增 DELETE 请求封装。
- 修改：`agent-frontend/src/store/modules/policyMarket.js`
  - 增加持久记录与本地 `pending-*` 临时记录的删除状态同步。
- 修改：`agent-frontend/src/views/policy-market/components/ConsultationHistory.vue`
  - 加入悬停/聚焦可见的删除图标按钮、独立可访问名称和 `delete` 事件。
- 修改：`agent-frontend/src/views/policy-market/index.vue`
  - 用 Element Plus 确认框协调删除动作，并提供成功/失败反馈。
- 修改：`agent-frontend/tests/policy-market-api.spec.js`
  - 覆盖删除请求 URL、HTTP 方法与响应数据解包。
- 修改：`agent-frontend/tests/policy-market-store.spec.js`
  - 覆盖持久记录、当前选中记录和临时记录的删除状态变化。
- 修改：`agent-frontend/tests/policy-market-components.spec.js`
  - 覆盖删除按钮事件不触发历史记录选择。
- 新增：`agent-frontend/tests/policy-market-page.spec.js`（仅在现有页面测试不能承载确认交互时）
  - 覆盖取消不删除、确认后调用 Store 并提示结果；优先扩展已有页面测试，不重复建立测试基础设施。

### Task 1：先锁定后端删除接口契约

**Files:**
- Modify: `agent-backend/tests/e2e/policy_market/test_consultation_endpoints.py:61-124`

- [ ] **Step 1：写入成功硬删除与数据库移除的失败测试**

在文件 import 区新增：

```python
from sqlalchemy import select
```

在现有详情隔离测试后添加：

```python
@pytest.mark.asyncio
async def test_delete_consultation_hard_deletes_current_users_record(consultation_client):
    response = await consultation_client.delete("/ir/policy-market/consultations/2")

    assert response.status_code == 200
    assert response.json()["data"] == {"id": 2, "deleted": True}

    records = (await consultation_client.get("/ir/policy-market/consultations")).json()["data"]
    assert [item["id"] for item in records] == [1]

    detail = await consultation_client.get("/ir/policy-market/consultations/2")
    assert detail.status_code == 404
```

- [ ] **Step 2：写入不存在与跨用户删除均返回 404 的失败测试**

紧接上一测试添加：

```python
@pytest.mark.asyncio
@pytest.mark.parametrize("record_id", [3, 999])
async def test_delete_consultation_returns_404_for_foreign_or_missing_record(
    consultation_client, record_id
):
    response = await consultation_client.delete(
        f"/ir/policy-market/consultations/{record_id}"
    )

    assert response.status_code == 404
    assert response.json()["data"] is None

    if record_id == 3:
        foreign = await consultation_client.get("/ir/policy-market/consultations/3")
        assert foreign.status_code == 404
```

- [ ] **Step 3：运行新增测试，确认其因端点尚不存在而失败**

从 `agent-backend/` 执行：

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/e2e/policy_market/test_consultation_endpoints.py', '-q', '-o', 'asyncio_mode=auto']))"
```

预期：新增 DELETE 测试失败，响应状态码为 405 或 404；既有 GET/POST 测试保持通过。

### Task 2：实现按用户归属的后端硬删除链路

**Files:**
- Modify: `agent-backend/app/modules/policy_market/domain/ports.py:6-19`
- Modify: `agent-backend/app/modules/policy_market/infrastructure/persistence/consultation_repository.py:1-67`
- Modify: `agent-backend/app/modules/policy_market/application/consultation_service.py:28-37`
- Modify: `agent-backend/app/modules/policy_market/interface/router.py:76-89`
- Test: `agent-backend/tests/e2e/policy_market/test_consultation_endpoints.py`

- [ ] **Step 1：扩展咨询记录仓储端口**

在 `ConsultationRepository` Protocol 的 `get_by_id_and_user()` 定义后添加：

```python
    async def delete_by_id_and_user(self, *, record_id: int, user_id: str) -> bool: ...
```

- [ ] **Step 2：实现仓储中的联合条件硬删除**

将 `consultation_repository.py` 的导入替换为：

```python
from sqlalchemy import delete, select
```

在 `get_by_id_and_user()` 后、`_require_row()` 前添加：

```python
    async def delete_by_id_and_user(self, *, record_id: int, user_id: str) -> bool:
        statement = delete(ConsultationRecordORM).where(
            ConsultationRecordORM.id == record_id,
            ConsultationRecordORM.user_id == user_id,
        )
        result = await self._session.execute(statement)
        return result.rowcount > 0
```

不要先按 ID 查询再删除；联合条件必须在同一条 DELETE 语句中，以避免泄露或删除非当前用户记录。

- [ ] **Step 3：在应用服务中委派删除动作**

在 `ConsultationService.get_for_user()` 后添加：

```python
    async def delete_for_user(self, *, record_id: int, user_id: str) -> bool:
        return await self._repository.delete_by_id_and_user(
            record_id=record_id,
            user_id=user_id,
        )
```

- [ ] **Step 4：新增 DELETE 路由和统一响应**

在 `get_consultation()` 后、`list_scrolling_messages()` 前添加：

```python
@router.delete("/consultations/{record_id}")
async def delete_consultation(
    record_id: int,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    deleted = await _consultation_service(session).delete_for_user(
        record_id=record_id,
        user_id=user.user_id,
    )
    if not deleted:
        raise NotFoundException("咨询记录不存在")
    await session.commit()
    return ok({"id": record_id, "deleted": True})
```

- [ ] **Step 5：运行后端端点测试，确认所有用例通过**

从 `agent-backend/` 执行：

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/e2e/policy_market/test_consultation_endpoints.py', '-q', '-o', 'asyncio_mode=auto']))"
```

预期：所有政策咨询端点测试通过，包括成功删除、删除后列表/详情不可见、跨用户 404 和缺失记录 404。

### Task 3：先锁定前端 API 与 Store 的删除状态契约

**Files:**
- Modify: `agent-frontend/tests/policy-market-api.spec.js:5-34`
- Modify: `agent-frontend/tests/policy-market-store.spec.js:6-12, 22-120`

- [ ] **Step 1：为 API 删除请求写入失败测试**

在 `policy-market-api.spec.js` 的导入中加入 `deleteConsultation`。将第一个测试名称改为 `咨询 API 使用后端列表、详情、创建和删除端点`，在其 mock 链末尾追加：

```javascript
      .mockResolvedValueOnce({ data: { id: 1, deleted: true } })
```

在现有三次调用断言后添加：

```javascript
    await expect(deleteConsultation(1)).resolves.toEqual({ id: 1, deleted: true })

    expect(request).toHaveBeenNthCalledWith(4, {
      url: '/ir/policy-market/consultations/1', method: 'delete',
    })
```

- [ ] **Step 2：为 Store 持久删除与当前阅读态重置写入失败测试**

在 `policy-market-store.spec.js` 的 API mock 对象增加：

```javascript
  deleteConsultation: vi.fn(),
```

在现有详情加载失败测试后添加：

```javascript
  it('删除当前持久记录后清理列表、详情缓存并退出阅读态', async () => {
    api.deleteConsultation.mockResolvedValue({ id: 'c-1', deleted: true })
    const store = usePolicyMarketStore()
    store.consultations = [
      { id: 'c-1', title: '当前问题', status: 'completed' },
      { id: 'c-2', title: '保留问题', status: 'completed' },
    ]
    store.consultationDetails = { 'c-1': { id: 'c-1', answer: '完整回答' } }
    store.selectedConsultationId = 'c-1'

    await store.removeConsultation('c-1')

    expect(api.deleteConsultation).toHaveBeenCalledWith('c-1')
    expect(store.consultations).toEqual([{ id: 'c-2', title: '保留问题', status: 'completed' }])
    expect(store.consultationDetails['c-1']).toBeUndefined()
    expect(store.selectedConsultationId).toBeNull()
  })
```

- [ ] **Step 3：为 `pending-*` 本地记录删除写入失败测试**

紧接上一测试添加：

```javascript
  it('删除本地 pending 记录时不调用后端并清理选中状态', async () => {
    const store = usePolicyMarketStore()
    store.consultations = [{ id: 'pending-1', title: '处理中问题', status: 'processing' }]
    store.consultationDetails = { 'pending-1': { id: 'pending-1', status: 'processing' } }
    store.selectedConsultationId = 'pending-1'

    await store.removeConsultation('pending-1')

    expect(api.deleteConsultation).not.toHaveBeenCalled()
    expect(store.consultations).toEqual([])
    expect(store.consultationDetails['pending-1']).toBeUndefined()
    expect(store.selectedConsultationId).toBeNull()
  })
```

- [ ] **Step 4：运行前端 API 和 Store 测试，确认因删除导出和 action 尚不存在而失败**

在 Bash 环境中先设置 Node 路径，然后从 `agent-frontend/` 执行：

```bash
export PATH="/e/openclaw/nodejs:$PATH"
node "E:/openclaw/nodejs/node_modules/npm/bin/npm-cli.js" exec vitest -- run tests/policy-market-api.spec.js tests/policy-market-store.spec.js
```

预期：测试失败，原因是 `deleteConsultation` 或 `removeConsultation` 尚未定义。

### Task 4：实现前端 API 与 Store 删除同步

**Files:**
- Modify: `agent-frontend/src/api/policyMarket.js:7-9`
- Modify: `agent-frontend/src/store/modules/policyMarket.js:2-8, 124-127`
- Test: `agent-frontend/tests/policy-market-api.spec.js`
- Test: `agent-frontend/tests/policy-market-store.spec.js`

- [ ] **Step 1：新增 DELETE API 封装**

在 `getConsultation()` 后添加：

```javascript
export function deleteConsultation(id) {
  return request({ url: `/ir/policy-market/consultations/${id}`, method: 'delete' }).then((response) => response.data)
}
```

- [ ] **Step 2：在 Store 引入删除 API**

将 API 导入块补充为：

```javascript
  deleteConsultation,
```

放在 `getConsultation` 与 `getConsultations` 之间，保持按咨询 API 分组。

- [ ] **Step 3：新增 Store 删除 action**

在 `startNewConsultation()` 前添加：

```javascript
    async removeConsultation(id) {
      const record = this.consultations.find((item) => item.id === id)
      if (!record) return
      if (!String(id).startsWith('pending-')) await deleteConsultation(id)
      this.consultations = this.consultations.filter((item) => item.id !== id)
      delete this.consultationDetails[id]
      if (this.selectedConsultationId === id) this.startNewConsultation()
    },
```

不得在 API 请求失败时更新 `consultations`、`consultationDetails` 或 `selectedConsultationId`；异常应向页面抛出以显示失败提示。

- [ ] **Step 4：运行 API 和 Store 测试，确认通过**

```bash
export PATH="/e/openclaw/nodejs:$PATH"
node "E:/openclaw/nodejs/node_modules/npm/bin/npm-cli.js" exec vitest -- run tests/policy-market-api.spec.js tests/policy-market-store.spec.js
```

预期：全部 API 与 Store 测试通过。

### Task 5：先锁定历史项删除按钮的独立事件行为

**Files:**
- Modify: `agent-frontend/tests/policy-market-components.spec.js:44-51`

- [ ] **Step 1：扩展历史列表组件测试，验证删除不触发选择**

将首个组件测试替换为：

```javascript
  it('历史列表发出新建、选择和删除事件，删除不触发选择', async () => {
    const wrapper = mount(ConsultationHistory, { props: { consultations: [{ id: 'c-1', title: '新能源消纳政策有何变化？', createdAt: '2026-07-23T10:42:00+08:00' }], selectedId: 'c-1' } })
    await wrapper.get('[aria-label="新建提问"]').trigger('click')
    await wrapper.get('[data-consultation-id="c-1"]').trigger('click')
    await wrapper.get('[aria-label="删除研究记录"]').trigger('click')

    expect(wrapper.emitted('new-question')).toHaveLength(1)
    expect(wrapper.emitted('select')).toEqual([['c-1']])
    expect(wrapper.emitted('delete')).toEqual([['c-1']])
  })
```

- [ ] **Step 2：运行该测试并确认因为删除按钮未实现而失败**

```bash
export PATH="/e/openclaw/nodejs:$PATH"
node "E:/openclaw/nodejs/node_modules/npm/bin/npm-cli.js" exec vitest -- run tests/policy-market-components.spec.js
```

预期：测试因找不到 `[aria-label="删除研究记录"]` 失败。若测试中仍存在当前已知的“宁夏”无关失败，也需记录为既有失败，不将其归因于本任务。

### Task 6：实现悬停可见、可访问的历史项删除入口

**Files:**
- Modify: `agent-frontend/src/views/policy-market/components/ConsultationHistory.vue:10-35, 55-62`
- Test: `agent-frontend/tests/policy-market-components.spec.js`

- [ ] **Step 1：引入删除图标并扩展组件事件**

将图标导入替换为：

```javascript
import { Plus, Trash2 } from '@lucide/vue'
```

将事件定义替换为：

```javascript
defineEmits(['new-question', 'select', 'delete'])
```

- [ ] **Step 2：将历史项内容包裹为文本区和删除按钮，阻止冒泡**

将当前历史项内的两个元素：

```vue
        <span class="pm-history__title">{{ item.title || item.question }}</span>
        <time>{{ formatHistoryTime(item.createdAt) }}</time>
```

替换为：

```vue
        <span class="pm-history__content">
          <span class="pm-history__title">{{ item.title || item.question }}</span>
          <time>{{ formatHistoryTime(item.createdAt) }}</time>
        </span>
        <button
          type="button"
          class="pm-history__delete"
          aria-label="删除研究记录"
          title="删除研究记录"
          @click.stop="$emit('delete', item.id)"
        >
          <Trash2 :size="15" />
        </button>
```

保留父级历史项的 `@click="$emit('select', item.id)"`；删除按钮只能经自身 `.stop` 发送 `delete`。

- [ ] **Step 3：添加删除按钮的视觉与键盘焦点样式**

在 `.pm-history__item` 规则后添加：

```css
.pm-history__content { min-width: 0; display: grid; gap: 7px; }
.pm-history__delete { position: absolute; top: 10px; right: 8px; width: 28px; height: 28px; display: grid; place-items: center; border: 0; border-radius: var(--xc-radius-sm); padding: 0; background: transparent; color: var(--xc-text-mute); cursor: pointer; opacity: 0; transition: opacity 160ms ease, background-color 160ms ease, color 160ms ease; }
.pm-history__item:hover .pm-history__delete, .pm-history__item:focus-within .pm-history__delete { opacity: 1; }
.pm-history__delete:hover, .pm-history__delete:focus-visible { background: color-mix(in srgb, var(--xc-status-danger) 16%, transparent); color: var(--xc-status-danger); outline: none; }
.pm-history__delete:focus-visible { box-shadow: 0 0 0 2px var(--xc-status-danger); }
```

将 `.pm-history__item` 现有的 `padding` 从：

```css
padding: 13px 10px 13px 12px;
```

改为：

```css
padding: 13px 44px 13px 12px;
```

以避免标题与删除按钮重叠。不要影响 `.pm-history__item::before` 选中强调条、现有 hover/active 样式或移动端横向列表行为。

- [ ] **Step 4：重新运行组件测试并记录结果**

```bash
export PATH="/e/openclaw/nodejs:$PATH"
node "E:/openclaw/nodejs/node_modules/npm/bin/npm-cli.js" exec vitest -- run tests/policy-market-components.spec.js
```

预期：新增删除事件断言通过；如仍仅有既存的“宁夏”渲染失败，记录为与本任务无关的基线问题。

### Task 7：接入确认弹窗、调用 Store 并补页面交互测试

**Files:**
- Modify: `agent-frontend/src/views/policy-market/index.vue:4, 37-70`
- Test: `agent-frontend/tests/policy-market-page.spec.js` 或现有最适合的页面级测试文件

- [ ] **Step 1：为确认与删除结果写入页面级失败测试**

先读取 `agent-frontend/tests/policy-market-page.spec.js` 并复用其中的 store、Element Plus 和组件 stub 模式。新增两个最小用例：

```javascript
it('取消删除历史研究时不调用 Store 删除动作', async () => {
  // 将 ElMessageBox.confirm mock 为 rejected Promise。
  // 触发 ConsultationHistory 的 delete 事件。
  // 断言 store.removeConsultation 未被调用。
})

it('确认删除历史研究后调用 Store 并显示成功提示', async () => {
  // 将 ElMessageBox.confirm mock 为 resolved Promise。
  // mock store.removeConsultation 为 resolved Promise。
  // 触发 ConsultationHistory 的 delete 事件。
  // 断言 removeConsultation 使用该 ID 调用，ElMessage.success 接收“已删除”。
})
```

若现有页面测试并未 mock `ConsultationHistory` 的 emit，则创建浅挂载页面并通过 `wrapper.findComponent(ConsultationHistory).vm.$emit('delete', 'c-1')` 触发事件；不要测试 Element Plus 内部实现。

- [ ] **Step 2：运行页面测试，确认因为事件绑定和处理器尚不存在而失败**

```bash
export PATH="/e/openclaw/nodejs:$PATH"
node "E:/openclaw/nodejs/node_modules/npm/bin/npm-cli.js" exec vitest -- run tests/policy-market-page.spec.js
```

预期：新增测试失败，原因是 `@delete` 未绑定或删除处理器不存在。

- [ ] **Step 3：绑定组件 delete 事件并引入确认框**

将页面模板的 `ConsultationHistory` 改为：

```vue
      <ConsultationHistory
        :consultations="store.consultations"
        :selected-id="store.selectedConsultationId"
        @new-question="handleNewQuestion"
        @select="handleSelectConsultation"
        @delete="handleDeleteConsultation"
      />
```

将 Element Plus 导入替换为：

```javascript
import { ElMessage, ElMessageBox } from 'element-plus'
```

- [ ] **Step 4：实现确认、删除和提示处理器**

在 `handleSelectConsultation()` 后添加：

```javascript
async function handleDeleteConsultation(id) {
  try {
    await ElMessageBox.confirm('删除后无法恢复，确认删除吗？', '删除历史研究', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }

  try {
    await store.removeConsultation(id)
    ElMessage.success('已删除')
  } catch (error) {
    ElMessage.error(error?.message || '删除失败，请稍后重试')
  }
}
```

- [ ] **Step 5：运行页面测试，确认确认与反馈行为通过**

```bash
export PATH="/e/openclaw/nodejs:$PATH"
node "E:/openclaw/nodejs/node_modules/npm/bin/npm-cli.js" exec vitest -- run tests/policy-market-page.spec.js
```

预期：取消操作不调用 Store；确认后传递正确 ID 并显示“已删除”；失败时不由页面清除前端状态，Store 会因 API 异常而保留原状态。

### Task 8：执行回归验证与人工验收

**Files:**
- Modify: 所有上述实现和测试文件

- [ ] **Step 1：运行全部政策与市场前端测试**

```bash
export PATH="/e/openclaw/nodejs:$PATH"
node "E:/openclaw/nodejs/node_modules/npm/bin/npm-cli.js" exec vitest -- run tests/policy-market-api.spec.js tests/policy-market-store.spec.js tests/policy-market-components.spec.js tests/policy-market-page.spec.js
```

预期：所有新增删除相关测试通过。若已知的 `ConsultationResult` “宁夏”渲染失败仍存在，明确报告其为本任务前后均复现的既有问题，不修改该无关功能。

- [ ] **Step 2：运行前端生产构建**

```bash
export PATH="/e/openclaw/nodejs:$PATH"
node "E:/openclaw/nodejs/node_modules/npm/bin/npm-cli.js" run build
```

预期：Vite 生产构建成功。记录依赖中的现有 `@vueuse/core` PURE 注释与大 chunk 警告，但不在本任务中处理。

- [ ] **Step 3：运行后端政策咨询端点回归测试**

```bash
cd /f/qjcode/investment-research-agent/agent-backend
.venv/Scripts/python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/e2e/policy_market/test_consultation_endpoints.py', '-q', '-o', 'asyncio_mode=auto']))"
```

预期：端点测试全部通过。

- [ ] **Step 4：进行人工验收**

启动前后端后进入“政策与市场”，用当前用户创建至少两条研究记录并验证：

1. 鼠标悬停和键盘 Tab 聚焦某一记录时，删除图标可见、可操作；未悬停未聚焦时不显示。
2. 点击删除图标不会打开或切换到该条历史记录。
3. 取消确认后，列表和数据库记录均不改变。
4. 确认删除非当前记录后，当前阅读内容不变；刷新页面后已删除记录不再出现。
5. 确认删除当前阅读记录后，页面回到新建提问状态；刷新页面后该记录不再出现。
6. 使用另一用户身份请求同一记录 ID 时，后端返回 404，原记录仍存在。

- [ ] **Step 5：记录验证结果，不执行 Git 写操作**

项目约束规定未经用户明确要求，不执行 `git add`、`git commit` 或 `git push`。交付时列明实际通过的测试、构建结果与任何既有失败；不要创建提交。

## 自检

- 已覆盖硬删除、确认取消、用户归属隔离、删除后数据库不可查询、当前选中状态复位、临时记录容错、键盘可达性及点击事件隔离。
- 不修改 ORM、手工 DDL 或 migration，因为此方案不增加列或修改表结构。
- 不引入批量删除、软删除、恢复入口或无关重构。
- 所有代码步骤使用当前文件的实际类名、函数名、响应壳与测试运行方式；未保留 TBD、TODO 或未定义实现。
