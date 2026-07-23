# 市场脉搏数据库接入 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将政策与市场模块右侧市场脉搏的模拟资讯替换为 `policy_market_scrolling_messages` 表中的有效真实记录，并移除“今日市场观察”。

**Architecture:** 新增独立的 `policy_market` 后端只读模块：基础设施层映射数据库表，应用层固定有效性筛选与排序规则，接口层返回 camelCase DTO。前端 API 层调用新接口，Store 保持现有加载状态，`MarketPulse` 直接展示接口数据的横幅、标签、发布时间与外链。

**Tech Stack:** FastAPI、SQLAlchemy 异步 ORM、Pydantic、httpx ASGITransport、Vue 3、Pinia、Axios、Vitest、Vue Test Utils。

---

## 文件结构

- Create: `agent-backend/app/modules/policy_market/domain/models.py` — 框架无关的 `ScrollingMessage` 领域对象。
- Create: `agent-backend/app/modules/policy_market/application/scrolling_message_service.py` — 有效记录查询、排序与 ORM 映射。
- Create: `agent-backend/app/modules/policy_market/infrastructure/persistence/orm.py` — `policy_market_scrolling_messages` ORM。
- Create: `agent-backend/app/modules/policy_market/interface/serializers.py` — DTO 与标签解析。
- Create: `agent-backend/app/modules/policy_market/interface/router.py` — `GET /ir/policy-market/messages`。
- Create: 各级 `__init__.py` — 新模块包标识。
- Modify: `agent-backend/app/main.py` — 注册政策与市场路由。
- Modify: `agent-backend/sql/ir_agent_schema.sql` — 增加同名表及索引 DDL。
- Create: `agent-backend/tests/unit/policy_market/test_scrolling_message_orm.py` — ORM 映射测试。
- Create: `agent-backend/tests/unit/policy_market/test_scrolling_message_service.py` — 过滤、排序和领域映射测试。
- Create: `agent-backend/tests/e2e/policy_market/test_scrolling_message_endpoints.py` — 接口响应壳与 DTO 测试。
- Modify: `agent-frontend/src/api/policyMarket.js` — 将 `getMarketNews` 改为请求薄封装。
- Modify: `agent-frontend/src/views/policy-market/index.vue` — 移除资讯详情弹窗状态和事件。
- Modify: `agent-frontend/src/views/policy-market/components/MarketPulse.vue` — 显示首条横幅、标签与外链；移除固定摘要。
- Delete: `agent-frontend/src/views/policy-market/components/NewsDetailDialog.vue` — 真实表不提供详情正文，删除不再使用的详情弹窗。
- Modify: `agent-frontend/tests/policy-market-api.spec.js` — 断言 API 请求行为与 DTO。
- Modify: `agent-frontend/tests/policy-market-store.spec.js` — 使用真实消息 DTO 验证 Store。
- Modify: `agent-frontend/tests/policy-market-components.spec.js` — 验证横幅、标签、外链和摘要移除。
- Modify: `agent-frontend/tests/policy-market-page.spec.js` — 验证页面不再依赖详情弹窗。
- Modify: `my_projects/政策与市场模块-功能与开发文档.md` — 更新数据契约和已接入范围。

### Task 1: 建立数据库映射与受管 DDL

**Files:**
- Create: `agent-backend/app/modules/policy_market/__init__.py`
- Create: `agent-backend/app/modules/policy_market/domain/__init__.py`
- Create: `agent-backend/app/modules/policy_market/infrastructure/__init__.py`
- Create: `agent-backend/app/modules/policy_market/infrastructure/persistence/__init__.py`
- Create: `agent-backend/app/modules/policy_market/infrastructure/persistence/orm.py`
- Create: `agent-backend/tests/unit/policy_market/test_scrolling_message_orm.py`
- Modify: `agent-backend/sql/ir_agent_schema.sql`

- [ ] **Step 1: 编写 ORM 失败测试**

```python
from sqlalchemy import DateTime, Integer, Numeric, String

from app.modules.policy_market.infrastructure.persistence.orm import ScrollingMessageORM


def test_scrolling_message_orm_maps_table_and_query_indexes():
    table = ScrollingMessageORM.__table__
    assert table.name == "policy_market_scrolling_messages"
    assert isinstance(table.c.title.type, String)
    assert table.c.title.type.length == 255
    assert isinstance(table.c.publish_time.type, DateTime)
    assert isinstance(table.c.rating.type, Numeric)
    assert (table.c.rating.type.precision, table.c.rating.type.scale) == (3, 2)
    assert isinstance(table.c.status.type, Integer)
    indexes = {index.name: tuple(column.name for column in index.columns) for index in table.indexes}
    assert indexes["idx_status_deleted_sort"] == ("is_deleted", "status", "sort_order", "rating")
    assert indexes["idx_province"] == ("province",)
    assert indexes["idx_expire_time"] == ("expire_time",)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd agent-backend && .venv\Scripts\python.exe -c "import sys, pytest; sys.stdout=sys.stderr; raise SystemExit(pytest.main(['tests/unit/policy_market/test_scrolling_message_orm.py', '-q']))"`

Expected: FAIL，原因是 `policy_market` 模块尚不存在。

- [ ] **Step 3: 实现最小 ORM 映射**

在 `orm.py` 中使用 `Base`，映射 `id`、标题、简介、链接、省份、发布时间、过期时间、状态、评分、排序、标签、JSON 扩展属性、逻辑删除及创建/更新时间。索引定义必须与建表 SQL 一致：

```python
class ScrollingMessageORM(Base):
    __tablename__ = "policy_market_scrolling_messages"
    __table_args__ = (
        Index("idx_status_deleted_sort", "is_deleted", "status", "sort_order", "rating"),
        Index("idx_province", "province"),
        Index("idx_expire_time", "expire_time"),
    )

    id: Mapped[int] = mapped_column(_PK, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(500))
    link_url: Mapped[str | None] = mapped_column(String(1000))
    province: Mapped[str | None] = mapped_column(String(50))
    publish_time: Mapped[datetime | None] = mapped_column(DateTime)
    expire_time: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), server_default="0.00")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
```

使用 `JSON` 映射 `extra_data`，用 `Integer` 映射状态和删除标记。创建空 `__init__.py` 文件以使包可导入。

- [ ] **Step 4: 将完整建表语句加入受管 schema**

在 `ir_agent_schema.sql` 的其他业务表之后加入用户提供的 `CREATE TABLE policy_market_scrolling_messages` 语句和三个索引；保持字段名、默认值、注释、字符集及排序规则与本次给定 DDL 一致。

- [ ] **Step 5: 运行 ORM 测试确认通过**

Run: `cd agent-backend && .venv\Scripts\python.exe -c "import sys, pytest; sys.stdout=sys.stderr; raise SystemExit(pytest.main(['tests/unit/policy_market/test_scrolling_message_orm.py', '-q']))"`

Expected: PASS。

- [ ] **Step 6: 提交此任务**

```bash
git add agent-backend/app/modules/policy_market agent-backend/sql/ir_agent_schema.sql agent-backend/tests/unit/policy_market/test_scrolling_message_orm.py
git commit -m "feat: add policy market message persistence"
```

### Task 2: 实现只读查询服务和 DTO 序列化

**Files:**
- Create: `agent-backend/app/modules/policy_market/domain/models.py`
- Create: `agent-backend/app/modules/policy_market/application/__init__.py`
- Create: `agent-backend/app/modules/policy_market/application/scrolling_message_service.py`
- Create: `agent-backend/app/modules/policy_market/interface/__init__.py`
- Create: `agent-backend/app/modules/policy_market/interface/serializers.py`
- Create: `agent-backend/tests/unit/policy_market/test_scrolling_message_service.py`

- [ ] **Step 1: 编写过滤、排序与标签序列化失败测试**

```python
@pytest.mark.asyncio
async def test_list_messages_returns_only_active_nonexpired_rows_in_display_order(session):
    now = datetime.now()
    session.add_all([
        ScrollingMessageORM(title="最高", status=1, is_deleted=0, sort_order=10, rating=Decimal("4.50"), publish_time=now, tags="政策, 储能"),
        ScrollingMessageORM(title="次高", status=1, is_deleted=0, sort_order=10, rating=Decimal("3.00"), publish_time=now),
        ScrollingMessageORM(title="已过期", status=1, is_deleted=0, expire_time=now - timedelta(seconds=1)),
        ScrollingMessageORM(title="禁用", status=0, is_deleted=0),
        ScrollingMessageORM(title="删除", status=1, is_deleted=1),
    ])
    await session.commit()

    messages = await ScrollingMessageService().list_messages(session, now=now)

    assert [message.title for message in messages] == ["最高", "次高"]
    assert serialize_messages(messages)[0]["tags"] == ["政策", "储能"]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd agent-backend && .venv\Scripts\python.exe -c "import sys, pytest; sys.stdout=sys.stderr; raise SystemExit(pytest.main(['tests/unit/policy_market/test_scrolling_message_service.py', '-q', '-o', 'asyncio_mode=auto']))"`

Expected: FAIL，原因是领域模型、服务和序列化函数不存在。

- [ ] **Step 3: 定义领域对象与查询服务**

`domain/models.py` 定义不可变 dataclass：

```python
@dataclass(frozen=True)
class ScrollingMessage:
    id: int
    title: str
    summary: str | None
    link_url: str | None
    province: str | None
    publish_time: datetime | None
    tags: str | None
```

服务以传入的 `now` 支持确定性测试，生产调用缺省 `datetime.now()`；查询必须严格使用以下条件和排序：

```python
statement = (
    select(ScrollingMessageORM)
    .where(
        ScrollingMessageORM.is_deleted == 0,
        ScrollingMessageORM.status == 1,
        or_(ScrollingMessageORM.expire_time.is_(None), ScrollingMessageORM.expire_time > now),
    )
    .order_by(
        ScrollingMessageORM.sort_order.desc(),
        ScrollingMessageORM.rating.desc(),
        ScrollingMessageORM.publish_time.desc(),
        ScrollingMessageORM.id.desc(),
    )
)
```

- [ ] **Step 4: 实现序列化器**

`serializers.py` 将字段转换为 `id`、`title`、`summary`、`linkUrl`、`province`、`publishTime` 和 `tags`。`tags` 对 `None` 或空白字符串返回 `[]`，否则按英文逗号分割、`strip()` 并剔除空项目；时间字段直接返回 `datetime.isoformat()` 或 `None`。

- [ ] **Step 5: 运行服务测试确认通过**

Run: `cd agent-backend && .venv\Scripts\python.exe -c "import sys, pytest; sys.stdout=sys.stderr; raise SystemExit(pytest.main(['tests/unit/policy_market/test_scrolling_message_service.py', '-q', '-o', 'asyncio_mode=auto']))"`

Expected: PASS。

- [ ] **Step 6: 提交此任务**

```bash
git add agent-backend/app/modules/policy_market/domain agent-backend/app/modules/policy_market/application agent-backend/app/modules/policy_market/interface/serializers.py agent-backend/tests/unit/policy_market/test_scrolling_message_service.py
git commit -m "feat: query active policy market messages"
```

### Task 3: 暴露并注册市场脉搏读取接口

**Files:**
- Create: `agent-backend/app/modules/policy_market/interface/router.py`
- Modify: `agent-backend/app/main.py:16-38`
- Create: `agent-backend/tests/e2e/policy_market/test_scrolling_message_endpoints.py`

- [ ] **Step 1: 编写端点失败测试**

```python
@pytest.mark.asyncio
async def test_list_scrolling_messages_returns_response_shell_and_camel_case_dto(seeded_client):
    response = await seeded_client.get("/ir/policy-market/messages")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert [item["title"] for item in body["data"]] == ["置顶资讯", "普通资讯"]
    assert body["data"][0] == {
        "id": 1,
        "title": "置顶资讯",
        "summary": "储能市场动态",
        "linkUrl": "https://example.test/top",
        "province": "内蒙古",
        "publishTime": "2026-07-23T09:00:00",
        "tags": ["政策", "储能"],
    }
```

测试 fixture 按 `test_tie_line_endpoints.py` 创建 `sqlite+aiosqlite:///:memory:`、`StaticPool`、`Base.metadata.create_all`，并覆盖 `get_db_session`。插入置顶、普通、过期、禁用和逻辑删除记录。请求必须带 `userId` 与 `username` Header。

- [ ] **Step 2: 运行测试确认失败**

Run: `cd agent-backend && .venv\Scripts\python.exe -c "import sys, pytest; sys.stdout=sys.stderr; raise SystemExit(pytest.main(['tests/e2e/policy_market/test_scrolling_message_endpoints.py', '-q', '-o', 'asyncio_mode=auto']))"`

Expected: FAIL，原因是路由尚未注册，返回 404。

- [ ] **Step 3: 实现路由并注册**

`router.py` 采用与联络线模块一致的依赖注入：

```python
router = APIRouter(prefix="/ir/policy-market", tags=["policy-market"])
_service = ScrollingMessageService()

@router.get("/messages")
async def list_scrolling_messages(session: AsyncSession = Depends(get_db_session)):
    messages = await _service.list_messages(session)
    return ok(serialize_messages(messages))
```

在 `app/main.py` 导入 `policy_market_router`，并在 `register_routers()` 里添加 `app.include_router(policy_market_router)`。不增加请求参数，也不加用户归属过滤，因为该表是公共栏目数据。

- [ ] **Step 4: 运行端点测试确认通过**

Run: `cd agent-backend && .venv\Scripts\python.exe -c "import sys, pytest; sys.stdout=sys.stderr; raise SystemExit(pytest.main(['tests/e2e/policy_market/test_scrolling_message_endpoints.py', '-q', '-o', 'asyncio_mode=auto']))"`

Expected: PASS。

- [ ] **Step 5: 提交此任务**

```bash
git add agent-backend/app/main.py agent-backend/app/modules/policy_market/interface/router.py agent-backend/tests/e2e/policy_market/test_scrolling_message_endpoints.py
git commit -m "feat: expose policy market message endpoint"
```

### Task 4: 用后端接口替换前端模拟资讯 API

**Files:**
- Modify: `agent-frontend/src/api/policyMarket.js`
- Modify: `agent-frontend/tests/policy-market-api.spec.js`

- [ ] **Step 1: 将 API 测试改为请求行为测试**

Mock `@/utils/request`，并断言：

```javascript
vi.mock('@/utils/request', () => ({ default: vi.fn() }))

it('读取市场脉搏消息时调用后端接口', async () => {
  request.mockResolvedValue([{ id: 1, title: '置顶资讯', tags: ['政策'] }])

  await expect(getMarketNews()).resolves.toEqual([{ id: 1, title: '置顶资讯', tags: ['政策'] }])
  expect(request).toHaveBeenCalledWith({ url: '/ir/policy-market/messages', method: 'get' })
})
```

删除对模拟 `marketNews` 数据及其 `category/content/source` 字段的断言；保留咨询和统计模拟 API 的现有测试。

- [ ] **Step 2: 运行测试确认失败**

Run: `cd agent-frontend && npm exec vitest -- run tests/policy-market-api.spec.js`

Expected: FAIL，因为 `getMarketNews` 仍返回延迟模拟数组且未调用 `request`。

- [ ] **Step 3: 以请求薄封装替换 `getMarketNews`**

保留咨询与统计函数，删除 `marketNews` 常量；添加请求导入并实现：

```javascript
import request from '@/utils/request'

export function getMarketNews() {
  return request({ url: '/ir/policy-market/messages', method: 'get' })
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd agent-frontend && npm exec vitest -- run tests/policy-market-api.spec.js`

Expected: PASS。

- [ ] **Step 5: 提交此任务**

```bash
git add agent-frontend/src/api/policyMarket.js agent-frontend/tests/policy-market-api.spec.js
git commit -m "feat: load policy market messages from backend"
```

### Task 5: 调整市场脉搏界面和页面集成

**Files:**
- Modify: `agent-frontend/src/views/policy-market/components/MarketPulse.vue`
- Modify: `agent-frontend/src/views/policy-market/index.vue`
- Delete: `agent-frontend/src/views/policy-market/components/NewsDetailDialog.vue`
- Modify: `agent-frontend/tests/policy-market-components.spec.js`
- Modify: `agent-frontend/tests/policy-market-page.spec.js`
- Modify: `agent-frontend/tests/policy-market-store.spec.js`

- [ ] **Step 1: 改写组件测试以覆盖真实消息展示**

使用如下消息 props，并断言横幅取首条标题、标签渲染、链接安全新开窗口、固定摘要不存在：

```javascript
news: [{
  id: 1,
  title: '置顶储能政策',
  summary: '储能市场动态',
  linkUrl: 'https://example.test/top',
  province: '内蒙古',
  publishTime: '2026-07-23T09:00:00',
  tags: ['政策', '储能'],
}]

expect(wrapper.text()).toContain('置顶储能政策')
expect(wrapper.text()).toContain('政策')
expect(wrapper.text()).not.toContain('今日市场观察')
expect(wrapper.get('[data-news-id="1"]').attributes('href')).toBe('https://example.test/top')
expect(wrapper.get('[data-news-id="1"]').attributes('target')).toBe('_blank')
```

新增无 `linkUrl` 用例，断言条目不是链接且无 `href`。删除 `open-news` 事件和 `NewsDetailDialog` 测试。

- [ ] **Step 2: 运行组件与页面测试确认失败**

Run: `cd agent-frontend && npm exec vitest -- run tests/policy-market-components.spec.js tests/policy-market-page.spec.js tests/policy-market-store.spec.js`

Expected: FAIL，因为组件仍使用 `category/publishedAt`、按钮点击事件和固定摘要，页面仍引用详情弹窗。

- [ ] **Step 3: 重构 `MarketPulse.vue` 展示逻辑**

- 新增 `tickerMessage` computed，取 `props.news[0]`。
- 横幅在有首条时显示 `tickerMessage.title`，无数据时显示“暂无滚动资讯”。
- 条目有 `linkUrl` 时渲染 `<a>`，带 `target="_blank" rel="noopener noreferrer"`；无链接时渲染无交互的 `<div>`。
- 标题使用 `title`；时间调用既有格式化函数但输入改为 `publishTime`；使用 `v-for="tag in item.tags"` 渲染标签。
- 移除 `defineEmits`、`@click`、`阅读详情`、`category` 引用及 `pm-pulse__summary` 的模板和样式。

核心模板结构：

```vue
<div class="pm-pulse__ticker">
  <span>滚动资讯</span>
  <span>{{ tickerMessage?.title || '暂无滚动资讯' }}</span>
</div>
<div class="pm-pulse__news">
  <template v-for="item in news" :key="item.id">
    <a v-if="item.linkUrl" :data-news-id="item.id" class="pm-pulse__news-item" :href="item.linkUrl" target="_blank" rel="noopener noreferrer">
      <strong>{{ item.title }}</strong>
      <span><b v-for="tag in item.tags" :key="tag">{{ tag }}</b>{{ formatPublishedAt(item.publishTime) }}</span>
    </a>
    <div v-else :data-news-id="item.id" class="pm-pulse__news-item">
      <strong>{{ item.title }}</strong>
      <span><b v-for="tag in item.tags" :key="tag">{{ tag }}</b>{{ formatPublishedAt(item.publishTime) }}</span>
    </div>
  </template>
</div>
```

- [ ] **Step 4: 移除页面详情弹窗耦合**

从 `index.vue` 移除 `NewsDetailDialog` 导入、`dialogVisible`、`selectedNewsId`、`selectedNews`、`handleOpenNews`、`@open-news` 和对话框模板。保留对 `MarketPulse` 的新闻、加载和错误 props 传递。

删除 `NewsDetailDialog.vue` 文件。

- [ ] **Step 5: 更新 Store 测试的资讯 DTO**

将 `getMarketNews` mock 数据改为新接口字段，例如：

```javascript
api.getMarketNews.mockResolvedValue([{ id: 1, title: '资讯', tags: [], publishTime: '2026-07-23T09:00:00' }])
```

Store 实现无需为 DTO 增加映射，继续直接赋值 `this.news = await getMarketNews()`。

- [ ] **Step 6: 运行前端定向测试确认通过**

Run: `cd agent-frontend && npm exec vitest -- run tests/policy-market-api.spec.js tests/policy-market-store.spec.js tests/policy-market-components.spec.js tests/policy-market-page.spec.js`

Expected: PASS。

- [ ] **Step 7: 提交此任务**

```bash
git add agent-frontend/src/views/policy-market agent-frontend/tests/policy-market-components.spec.js agent-frontend/tests/policy-market-page.spec.js agent-frontend/tests/policy-market-store.spec.js
git rm agent-frontend/src/views/policy-market/components/NewsDetailDialog.vue
git commit -m "feat: render market pulse from database messages"
```

### Task 6: 同步模块文档并执行全量验证

**Files:**
- Modify: `my_projects/政策与市场模块-功能与开发文档.md`

- [ ] **Step 1: 更新模块文档的数据契约和范围说明**

将“首版范围”由完全模拟数据改为：咨询记录和统计仍为模拟实现，市场脉搏已读取 `policy_market_scrolling_messages` 表。将市场资讯 DTO 替换为：

```js
{
  id: 1,
  title: '...',
  summary: '...' || null,
  linkUrl: '...' || null,
  province: '...' || null,
  publishTime: '2026-07-23T09:00:00' || null,
  tags: ['政策', '储能']
}
```

写明固定筛选 `is_deleted=0`、`status=1`、未过期，以及 `sort_order`、`rating`、`publish_time`、`id` 的降序规则；删除详情弹窗与“今日市场观察”的描述。

- [ ] **Step 2: 运行后端政策与市场测试**

Run: `cd agent-backend && .venv\Scripts\python.exe -c "import sys, pytest; sys.stdout=sys.stderr; raise SystemExit(pytest.main(['tests/unit/policy_market', 'tests/e2e/policy_market', '-q', '-o', 'asyncio_mode=auto']))"`

Expected: PASS。

- [ ] **Step 3: 运行前端政策与市场测试和构建**

Run: `cd agent-frontend && npm exec vitest -- run tests/policy-market-api.spec.js tests/policy-market-store.spec.js tests/policy-market-components.spec.js tests/policy-market-page.spec.js && npm run build`

Expected: 所有测试 PASS，构建退出码为 0；可记录既有 Rollup 大分包警告但不得当作失败。

- [ ] **Step 4: 运行后端全量测试**

Run: `cd agent-backend && .venv\Scripts\python.exe -c "import sys, pytest; sys.stdout=sys.stderr; raise SystemExit(pytest.main(['-q', '-o', 'asyncio_mode=auto']))"`

Expected: PASS；若出现与本次改动无关的已有失败，记录精确失败用例和输出，不掩盖失败。

- [ ] **Step 5: 提交文档与验证后的最终变更**

```bash
git add my_projects/政策与市场模块-功能与开发文档.md
git commit -m "docs: document policy market message data source"
```
