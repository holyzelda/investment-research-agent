# 政策与市场咨询历史持久化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将政策与市场模块的真实问答结果按当前平台用户持久化到本地数据库，并提供创建、历史列表和单条详情能力。

**Architecture:** 在 `policy_market` 模块内新增咨询记录领域模型、SQLAlchemy ORM、SQL 仓储、可替换的问答执行器端口与应用服务。HTTP 路由仅处理请求校验、平台身份依赖和统一响应壳；应用服务创建处理中记录，在线程中调用 `tools.policy_ask.ask(question)`，将成功结果或失败状态持久化。前端移除咨询 mock，经 API 模块和 Pinia Store 实现列表、按需详情和提交状态。

**Tech Stack:** Python 3.13、FastAPI、SQLAlchemy Async、SQLite（测试）、MySQL 8（DDL）、httpx ASGITransport、Vue 3、Pinia、Axios、Vitest。

---

## 文件结构

### 后端

- 修改：`agent-backend/app/modules/policy_market/domain/models.py` — 新增不可变咨询记录领域 DTO 与问答结果 DTO。
- 创建：`agent-backend/app/modules/policy_market/domain/ports.py` — 定义异步咨询记录仓储与同步问答执行器端口，domain 不依赖 FastAPI、SQLAlchemy 或工具脚本。
- 修改：`agent-backend/app/modules/policy_market/infrastructure/persistence/orm.py` — 新增 `ConsultationRecordORM`，以及用户时间倒序索引。
- 创建：`agent-backend/app/modules/policy_market/infrastructure/persistence/consultation_repository.py` — SQLAlchemy 仓储，实现创建、更新、本人列表和本人详情读取。
- 创建：`agent-backend/app/modules/policy_market/infrastructure/policy_ask_executor.py` — 将 `tools.policy_ask.ask` 映射为领域问答结果；只在基础设施层导入工具脚本。
- 创建：`agent-backend/app/modules/policy_market/application/consultation_service.py` — 编排创建、线程执行问答、结果冻结与归属读取。
- 修改：`agent-backend/app/modules/policy_market/interface/serializers.py` — 增加列表摘要与详情 DTO 的 camelCase 序列化。
- 修改：`agent-backend/app/modules/policy_market/interface/router.py` — 添加 `POST /consultations`、`GET /consultations`、`GET /consultations/{record_id}`。
- 修改：`agent-backend/app/core/config/settings.py` — 添加只包含非敏感行为开关/超时的政策问答配置（若执行器需要）；机密仅经环境变量/Nacos 注入。
- 修改：`agent-backend/tools/policy_ask.py` — 移除源码中的明文凭据；从运行时环境变量读取，缺少必填配置时抛出可诊断异常。不得把敏感值迁移到 YAML、DDL、测试或文档。
- 修改：`agent-backend/sql/ir_agent_schema.sql` — 新增 MySQL 8 的 `consultation_records` 表和 `idx_consultation_user_time`。
- 创建：`agent-backend/tests/unit/policy_market/test_consultation_service.py` — 不接触数据库/飞书/LLM 的应用服务单元测试。
- 创建：`agent-backend/tests/e2e/policy_market/test_consultation_endpoints.py` — SQLite + ASGITransport 端到端测试。

### 前端

- 修改：`agent-frontend/src/api/policyMarket.js` — 删除咨询 mock 和延时器，新增三个真实 HTTP 封装。
- 修改：`agent-frontend/src/store/modules/policyMarket.js` — 添加详情状态/请求，并以真实 DTO 维护乐观提交和列表刷新。
- 修改：`agent-frontend/src/views/policy-market/components/ConsultationResult.vue` — 从 `sourceData` 展示来源快照与时效/提醒，不再依赖 `sourceScope`。
- 修改：`agent-frontend/tests/policy-market-api.spec.js` — 验证 API URL、方法、请求体和 DTO 解包。
- 修改：`agent-frontend/tests/policy-market-store.spec.js` — 验证按需详情加载、成功刷新及失败状态。
- 修改：`agent-frontend/tests/policy-market-components.spec.js` — 验证完成态按新 `sourceData` 显示来源信息。
- 修改：`my_projects/investment-research-agent-项目开发指南.md` — 将“咨询 API 为模拟实现”的描述更新为持久化接口和真实问答接入说明。

## Task 1: 定义领域契约与持久化结构

**Files:**
- Modify: `agent-backend/app/modules/policy_market/domain/models.py`
- Create: `agent-backend/app/modules/policy_market/domain/ports.py`
- Modify: `agent-backend/app/modules/policy_market/infrastructure/persistence/orm.py`
- Modify: `agent-backend/sql/ir_agent_schema.sql`
- Test: `agent-backend/tests/unit/policy_market/test_consultation_service.py`

- [ ] **Step 1: 编写领域 DTO 与仓储端口的失败测试**

在 `agent-backend/tests/unit/policy_market/test_consultation_service.py` 写入最小导入测试，先锁定 domain 不依赖 SQLAlchemy：

```python
from app.modules.policy_market.domain.models import ConsultationRecord, ConsultationAnswer
from app.modules.policy_market.domain.ports import ConsultationRepository, PolicyAskExecutor


def test_consultation_domain_contract_is_importable_without_infrastructure():
    answer = ConsultationAnswer(
        answer="回答",
        province_code="宁夏",
        source_data={"sources": [], "timeliness": {}, "reminders": []},
    )
    record = ConsultationRecord(
        id=1,
        user_id="user-1",
        question="宁夏现货市场如何？",
        answer=answer.answer,
        province_code=answer.province_code,
        topic=None,
        status="completed",
        source_data=answer.source_data,
        created_at=None,
        answered_at=None,
        updated_at=None,
    )
    assert record.status == "completed"
    assert ConsultationRepository is not None
    assert PolicyAskExecutor is not None
```

- [ ] **Step 2: 运行测试确认失败**

在 `agent-backend/` 目录运行：

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/policy_market/test_consultation_service.py', '-q']))"
```

预期：失败，提示 `ConsultationRecord`、`ConsultationAnswer` 或 `ports` 模块尚不存在。

- [ ] **Step 3: 实现最小领域 DTO 和端口**

在 `domain/models.py` 追加以下类型；时间字段允许 `None`，使创建中的记录可表达：

```python
from typing import Any, Protocol


@dataclass(frozen=True)
class ConsultationAnswer:
    answer: str
    province_code: str | None
    source_data: dict[str, Any]


@dataclass(frozen=True)
class ConsultationRecord:
    id: int
    user_id: str
    question: str
    answer: str | None
    province_code: str | None
    topic: str | None
    status: str
    source_data: dict[str, Any] | None
    created_at: datetime | None
    answered_at: datetime | None
    updated_at: datetime | None
```

创建 `domain/ports.py`：

```python
from typing import Protocol

from app.modules.policy_market.domain.models import ConsultationAnswer, ConsultationRecord


class ConsultationRepository(Protocol):
    async def create_processing(self, *, user_id: str, question: str) -> ConsultationRecord: ...
    async def mark_completed(self, *, record_id: int, answer: ConsultationAnswer) -> ConsultationRecord: ...
    async def mark_failed(self, *, record_id: int) -> ConsultationRecord: ...
    async def list_by_user(self, *, user_id: str) -> list[ConsultationRecord]: ...
    async def get_by_id_and_user(self, *, record_id: int, user_id: str) -> ConsultationRecord | None: ...


class PolicyAskExecutor(Protocol):
    def ask(self, question: str) -> ConsultationAnswer: ...
```

`Protocol` 应从 `typing` 导入，不能在 `models.py` 保留未使用的 `Protocol` 导入。

- [ ] **Step 4: 增加 ORM 模型与索引**

在 `infrastructure/persistence/orm.py` 的 `_PK` 之后新增：

```python
class ConsultationRecordORM(Base):
    __tablename__ = "consultation_records"
    __table_args__ = (
        Index("idx_consultation_user_time", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(_PK, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    province_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    topic: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="processing")
    source_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    answered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
```

保持现有 `_PK` 的 SQLite 兼容策略。`user_id` 必须为 `String(64)`，与平台身份和会话表一致，不得按初始 SQL 草案错误改为 `BIGINT`。

- [ ] **Step 5: 同步 MySQL 手工 DDL**

在 `sql/ir_agent_schema.sql` 的适当建表区域添加：

```sql
CREATE TABLE consultation_records (
    id BIGINT NOT NULL AUTO_INCREMENT,
    user_id VARCHAR(64) NOT NULL,
    question TEXT NOT NULL,
    answer TEXT,
    province_code VARCHAR(20),
    topic VARCHAR(50),
    status VARCHAR(20) NOT NULL DEFAULT 'processing',
    source_data JSON,
    created_at DATETIME NOT NULL DEFAULT now(),
    answered_at DATETIME,
    updated_at DATETIME NOT NULL DEFAULT now() ON UPDATE now(),
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE INDEX idx_consultation_user_time ON consultation_records (user_id, created_at DESC);
```

不添加省份索引；当前不存在按省份查询需求。

- [ ] **Step 6: 运行领域测试与架构路径守护**

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/policy_market/test_consultation_service.py', 'tests/unit/test_architecture_layout.py', '-q']))"
```

预期：全部通过。

- [ ] **Step 7: 提交检查点（仅在用户明确授权 Git 写操作时执行）**

项目规则禁止未授权的 `git add`、`git commit`、`git push`。获得明确授权后执行：

```bash
git add agent-backend/app/modules/policy_market/domain/models.py agent-backend/app/modules/policy_market/domain/ports.py agent-backend/app/modules/policy_market/infrastructure/persistence/orm.py agent-backend/sql/ir_agent_schema.sql agent-backend/tests/unit/policy_market/test_consultation_service.py
git commit -m "feat: add consultation record persistence model"
```

## Task 2: 实现仓储与应用服务的成功/失败状态机

**Files:**
- Create: `agent-backend/app/modules/policy_market/infrastructure/persistence/consultation_repository.py`
- Create: `agent-backend/app/modules/policy_market/application/consultation_service.py`
- Modify: `agent-backend/tests/unit/policy_market/test_consultation_service.py`

- [ ] **Step 1: 编写应用服务的成功与失败测试**

在测试文件中定义内存替身，验证创建、冻结和失败状态：

```python
class FakeRepository:
    def __init__(self):
        self.records = {}
        self.next_id = 1

    async def create_processing(self, *, user_id, question):
        record = ConsultationRecord(self.next_id, user_id, question, None, None, None, "processing", None, None, None, None)
        self.records[record.id] = record
        self.next_id += 1
        return record

    async def mark_completed(self, *, record_id, answer):
        old = self.records[record_id]
        record = ConsultationRecord(old.id, old.user_id, old.question, answer.answer, answer.province_code, None, "completed", answer.source_data, None, None, None)
        self.records[record_id] = record
        return record

    async def mark_failed(self, *, record_id):
        old = self.records[record_id]
        record = ConsultationRecord(old.id, old.user_id, old.question, None, None, None, "failed", None, None, None, None)
        self.records[record_id] = record
        return record


class FakeExecutor:
    def ask(self, question):
        return ConsultationAnswer("结构化回答", "宁夏", {"sources": ["https://example.test/a"], "timeliness": {}, "reminders": []})


@pytest.mark.asyncio
async def test_create_persists_completed_answer_snapshot():
    service = ConsultationService(repository=FakeRepository(), executor=FakeExecutor())
    record = await service.create(user_id="u-1", question="宁夏政策")
    assert record.status == "completed"
    assert record.answer == "结构化回答"
    assert record.source_data["sources"] == ["https://example.test/a"]


@pytest.mark.asyncio
async def test_create_marks_record_failed_when_executor_raises():
    class BrokenExecutor:
        def ask(self, question):
            raise RuntimeError("上游不可用")

    repository = FakeRepository()
    service = ConsultationService(repository=repository, executor=BrokenExecutor())
    with pytest.raises(ConsultationExecutionError, match="政策与市场咨询暂时不可用"):
        await service.create(user_id="u-1", question="宁夏政策")
    assert repository.records[1].status == "failed"
    assert repository.records[1].answer is None
```

- [ ] **Step 2: 运行测试确认失败**

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/policy_market/test_consultation_service.py', '-q']))"
```

预期：失败，提示 `ConsultationService` 和 `ConsultationExecutionError` 不存在。

- [ ] **Step 3: 实现 SQLAlchemy 仓储**

创建 `consultation_repository.py`。实现应使用传入的 `AsyncSession`，每次状态变更调用 `flush()`，但由路由请求生命周期/调用方提交事务。核心查询如下：

```python
statement = (
    select(ConsultationRecordORM)
    .where(ConsultationRecordORM.user_id == user_id)
    .order_by(ConsultationRecordORM.created_at.desc(), ConsultationRecordORM.id.desc())
)
```

详情查询必须同时带 `id` 与 `user_id`：

```python
statement = select(ConsultationRecordORM).where(
    ConsultationRecordORM.id == record_id,
    ConsultationRecordORM.user_id == user_id,
)
```

完成更新必须原子地写入 `answer`、`province_code`、`source_data`、`status="completed"`、`answered_at=datetime.now()`；失败更新仅写入 `status="failed"`。将 ORM 映射为 `ConsultationRecord` 的私有函数命名为 `_to_domain(row)`。

- [ ] **Step 4: 实现应用服务，并在线程中运行同步问答**

创建 `consultation_service.py`：

```python
import asyncio

from app.modules.policy_market.domain.models import ConsultationRecord
from app.modules.policy_market.domain.ports import ConsultationRepository, PolicyAskExecutor


class ConsultationExecutionError(Exception):
    pass


class ConsultationService:
    def __init__(self, *, repository: ConsultationRepository, executor: PolicyAskExecutor):
        self._repository = repository
        self._executor = executor

    async def create(self, *, user_id: str, question: str) -> ConsultationRecord:
        record = await self._repository.create_processing(user_id=user_id, question=question)
        try:
            answer = await asyncio.to_thread(self._executor.ask, question)
        except Exception as exc:
            await self._repository.mark_failed(record_id=record.id)
            raise ConsultationExecutionError("政策与市场咨询暂时不可用，请稍后重试") from exc
        return await self._repository.mark_completed(record_id=record.id, answer=answer)

    async def list_for_user(self, *, user_id: str) -> list[ConsultationRecord]:
        return await self._repository.list_by_user(user_id=user_id)

    async def get_for_user(self, *, record_id: int, user_id: str) -> ConsultationRecord | None:
        return await self._repository.get_by_id_and_user(record_id=record_id, user_id=user_id)
```

不要把 `AsyncSession`、SQLAlchemy 查询、FastAPI 异常或 `tools.policy_ask` 导入到 domain；不要以 subprocess 调用 `policy_ask.main()`。

- [ ] **Step 5: 运行服务单元测试确认通过**

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/policy_market/test_consultation_service.py', '-q', '-o', 'asyncio_mode=auto']))"
```

预期：全部通过；测试不发起飞书下载或 LLM 请求。

- [ ] **Step 6: 提交检查点（仅在用户明确授权后）**

```bash
git add agent-backend/app/modules/policy_market/infrastructure/persistence/consultation_repository.py agent-backend/app/modules/policy_market/application/consultation_service.py agent-backend/tests/unit/policy_market/test_consultation_service.py
git commit -m "feat: persist policy consultations through service"
```

## Task 3: 封装真实问答执行器并移除工具脚本明文密钥

**Files:**
- Create: `agent-backend/app/modules/policy_market/infrastructure/policy_ask_executor.py`
- Modify: `agent-backend/tools/policy_ask.py`
- Modify: `agent-backend/app/core/config/settings.py`
- Test: `agent-backend/tests/unit/policy_market/test_policy_ask_executor.py`

- [ ] **Step 1: 编写执行器的失败测试**

新建 `test_policy_ask_executor.py`，通过 monkeypatch 替换工具模块函数，验证字段映射：

```python
from app.modules.policy_market.infrastructure.policy_ask_executor import PolicyAskExecutorAdapter


def test_executor_maps_tools_answer_to_domain(monkeypatch):
    monkeypatch.setattr(
        "app.modules.policy_market.infrastructure.policy_ask_executor.policy_ask.ask",
        lambda question: {
            "answer": "宁夏结论",
            "sources": ["https://example.test/source"],
            "timeliness": {"province": "宁夏", "as_of": "2026-07", "status": "已核验"},
            "reminders": ["关注更新"],
        },
    )

    result = PolicyAskExecutorAdapter().ask("宁夏政策")

    assert result.answer == "宁夏结论"
    assert result.province_code == "宁夏"
    assert result.source_data == {
        "sources": ["https://example.test/source"],
        "timeliness": {"province": "宁夏", "as_of": "2026-07", "status": "已核验"},
        "reminders": ["关注更新"],
    }
```

- [ ] **Step 2: 运行测试确认失败**

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/policy_market/test_policy_ask_executor.py', '-q']))"
```

预期：失败，提示执行器模块不存在。

- [ ] **Step 3: 实现基础设施执行器**

创建 `policy_ask_executor.py`。仅此文件导入 `tools.policy_ask`：

```python
from tools import policy_ask

from app.modules.policy_market.domain.models import ConsultationAnswer


class PolicyAskExecutorAdapter:
    def ask(self, question: str) -> ConsultationAnswer:
        result = policy_ask.ask(question)
        timeliness = result.get("timeliness") or {}
        return ConsultationAnswer(
            answer=str(result.get("answer") or ""),
            province_code=timeliness.get("province"),
            source_data={
                "sources": list(result.get("sources") or []),
                "timeliness": timeliness,
                "reminders": list(result.get("reminders") or []),
            },
        )
```

不得让前端、路由或 application service 直接导入该工具。

- [ ] **Step 4: 将问答工具机密改为环境变量并验证缺失配置**

在 `tools/policy_ask.py`：

1. 删除硬编码的飞书应用 ID、飞书应用密钥、知识库 token、LLM API key 与任何默认的生产/测试凭据。
2. 将 `APP_ID`、`APP_SECRET`、`INDEX_TOKEN`、`LLM_API_KEY` 等必需项改为对应环境变量读取，空值保持为空字符串。
3. 在 `_get_client()` 和调用 LLM/下载知识库前调用单一校验函数，例如 `_require_config("KB_ASK_APP_ID", APP_ID)`；未配置时抛出 `RuntimeError("缺少政策知识库配置：KB_ASK_APP_ID")`。
4. `LLM_BASE_URL` 和 `LLM_MODEL` 可保留非敏感默认值，但 API key 不得提供默认值。
5. 不在 `configs/application.yml`、测试源、文档或提交记录中写入真实值。

在 `settings.py` 中仅在确有执行器配置需求时增加非敏感 `PolicyAskConfig`，例如 `enabled` 和 `timeout_seconds`，并以 `_business_value` 支持环境变量/Nacos。机密保持由工具脚本运行时环境读取，避免在 `Settings` 日志或 repr 中意外输出。

- [ ] **Step 5: 运行执行器测试与明文扫描**

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/policy_market/test_policy_ask_executor.py', '-q']))"
git diff --check
```

预期：执行器测试通过；`git diff --check` 无空白错误。人工审查 diff，确认没有新增或保留工具中的原始凭据字符串。

- [ ] **Step 6: 提交检查点（仅在用户明确授权后）**

```bash
git add agent-backend/app/modules/policy_market/infrastructure/policy_ask_executor.py agent-backend/tools/policy_ask.py agent-backend/app/core/config/settings.py agent-backend/tests/unit/policy_market/test_policy_ask_executor.py
git commit -m "feat: integrate configured policy knowledge executor"
```

## Task 4: 增加咨询 HTTP 接口与归属隔离

**Files:**
- Modify: `agent-backend/app/modules/policy_market/interface/serializers.py`
- Modify: `agent-backend/app/modules/policy_market/interface/router.py`
- Create: `agent-backend/tests/e2e/policy_market/test_consultation_endpoints.py`

- [ ] **Step 1: 编写端到端失败测试**

参考 `tests/e2e/policy_market/test_scrolling_message_endpoints.py` 创建内存 SQLite fixture：运行 `Base.metadata.create_all`，覆盖 `get_db_session`，并用 `ASGITransport(app=app)` 创建带 `userId` 和 `username` Header 的 `AsyncClient`。

覆盖以下行为：

```python
@pytest.mark.asyncio
async def test_consultations_only_return_current_users_records(seeded_client):
    response = await seeded_client.get("/ir/policy-market/consultations")
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data"]] == [2, 1]
    assert all("answer" not in item for item in response.json()["data"])


@pytest.mark.asyncio
async def test_consultation_detail_returns_404_for_another_users_record(seeded_client):
    response = await seeded_client.get("/ir/policy-market/consultations/3")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_consultation_endpoints_require_platform_identity(seeded_client):
    response = await seeded_client.get("/ir/policy-market/consultations", headers={"userId": "", "username": ""})
    assert response.status_code == 401
```

为 POST 用 `monkeypatch` 替换 router/service 组装所使用的执行器，避免真实外部调用，并断言：成功响应 `code == 200`、`status == "completed"`、`sourceData` 完整；空问题得到 HTTP 400；执行器异常后数据库行状态为 `failed`。

- [ ] **Step 2: 运行端到端测试确认失败**

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/e2e/policy_market/test_consultation_endpoints.py', '-q', '-o', 'asyncio_mode=auto']))"
```

预期：失败，路由尚未注册 `consultations` 端点。

- [ ] **Step 3: 添加序列化函数**

在 `serializers.py` 添加 `serialize_consultation_summary(record)` 与 `serialize_consultation_detail(record)`，使用以下字段名：

```python
def serialize_consultation_summary(record):
    return {
        "id": record.id,
        "title": record.question,
        "question": record.question,
        "status": record.status,
        "createdAt": record.created_at.isoformat() if record.created_at else None,
        "answeredAt": record.answered_at.isoformat() if record.answered_at else None,
    }


def serialize_consultation_detail(record):
    return {
        **serialize_consultation_summary(record),
        "answer": record.answer,
        "provinceCode": record.province_code,
        "topic": record.topic,
        "sourceData": record.source_data,
    }
```

`title` 本期等于完整问题，不引入截断规则；页面可按现有样式自行截断显示。

- [ ] **Step 4: 在路由中组装服务、校验请求并映射异常**

新增 Pydantic 请求模型：

```python
class ConsultationCreateRequest(BaseModel):
    question: str
```

创建一个私有工厂 `_consultation_service(session)`，注入 `SqlAlchemyConsultationRepository(session)` 与 `PolicyAskExecutorAdapter()`。接口签名使用既有：

```python
user: CurrentUser = Depends(get_current_user)
session: AsyncSession = Depends(get_db_session)
```

实现要求：

- `POST /consultations`：`question = payload.question.strip()`；为空时抛出 `ValidationException("请输入政策或市场问题")`；调用 `service.create`；成功后 `await session.commit()`，返回 `ok(serialize_consultation_detail(record))`；捕获 `ConsultationExecutionError` 后仍须 `await session.commit()` 以保存 `failed`，再转换为项目已有业务异常类型，使 HTTP 为 400 且响应壳一致。
- `GET /consultations`：返回 `ok([serialize_consultation_summary(item) for item in records])`。
- `GET /consultations/{record_id}`：调用 `get_for_user`；返回 `None` 时抛出项目已有 404 异常类型；不要先按 ID 单独查询后再检查用户。

实现前读取 `app/core/exceptions.py`，选用既有 400/404 异常类；禁止直接生成 FastAPI 默认 422/500 响应。

- [ ] **Step 5: 运行端到端测试确认通过**

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/e2e/policy_market/test_consultation_endpoints.py', 'tests/e2e/policy_market/test_scrolling_message_endpoints.py', '-q', '-o', 'asyncio_mode=auto']))"
```

预期：全部通过，且不访问飞书或 LLM。

- [ ] **Step 6: 提交检查点（仅在用户明确授权后）**

```bash
git add agent-backend/app/modules/policy_market/interface/serializers.py agent-backend/app/modules/policy_market/interface/router.py agent-backend/tests/e2e/policy_market/test_consultation_endpoints.py
git commit -m "feat: expose owned policy consultation endpoints"
```

## Task 5: 将前端 API 与 Store 改为真实咨询数据流

**Files:**
- Modify: `agent-frontend/src/api/policyMarket.js`
- Modify: `agent-frontend/src/store/modules/policyMarket.js`
- Modify: `agent-frontend/tests/policy-market-api.spec.js`
- Modify: `agent-frontend/tests/policy-market-store.spec.js`

- [ ] **Step 1: 编写 API 模块失败测试**

在 `policy-market-api.spec.js` mock `@/utils/request`，替换原先 mock 数据断言为：

```javascript
it('咨询 API 使用后端列表、详情和创建端点', async () => {
  request.mockResolvedValueOnce({ data: [{ id: 1 }] })
  request.mockResolvedValueOnce({ data: { id: 1, answer: '回答' } })
  request.mockResolvedValueOnce({ data: { id: 2, answer: '新回答' } })

  await expect(getConsultations()).resolves.toEqual([{ id: 1 }])
  await expect(getConsultation(1)).resolves.toEqual({ id: 1, answer: '回答' })
  await expect(submitConsultation({ question: '宁夏政策' })).resolves.toEqual({ id: 2, answer: '新回答' })

  expect(request).toHaveBeenNthCalledWith(1, { url: '/ir/policy-market/consultations', method: 'get' })
  expect(request).toHaveBeenNthCalledWith(2, { url: '/ir/policy-market/consultations/1', method: 'get' })
  expect(request).toHaveBeenNthCalledWith(3, {
    url: '/ir/policy-market/consultations', method: 'post', data: { question: '宁夏政策' },
  })
})
```

- [ ] **Step 2: 运行前端 API 测试确认失败**

在 `agent-frontend/` 目录运行：

```bash
pnpm exec vitest -- run tests/policy-market-api.spec.js
```

预期：失败，`getConsultation` 尚未导出，或请求 URL/方法仍是 mock。

- [ ] **Step 3: 替换咨询 mock 为真实请求封装**

删除 `delay`、`consultations` 和本地时间 ID 生成。新增：

```javascript
export function getConsultations() {
  return request({ url: '/ir/policy-market/consultations', method: 'get' }).then((response) => response.data)
}

export function getConsultation(id) {
  return request({ url: `/ir/policy-market/consultations/${id}`, method: 'get' }).then((response) => response.data)
}

export function submitConsultation({ question }) {
  const normalizedQuestion = String(question || '').trim()
  if (!normalizedQuestion) return Promise.reject(new Error('请输入政策或市场问题'))
  return request({
    url: '/ir/policy-market/consultations',
    method: 'post',
    data: { question: normalizedQuestion },
  }).then((response) => response.data)
}
```

保留资讯相关函数不变。

- [ ] **Step 4: 为 Store 详情加载写失败测试**

在 mock 定义增加 `getConsultation: vi.fn()`。新增：

```javascript
it('选择历史项时按需加载并替换为完整详情', async () => {
  api.getConsultation.mockResolvedValue({
    id: 'c-1', title: '问题', question: '问题', answer: '完整回答',
    status: 'completed', sourceData: { sources: [] },
  })
  const store = usePolicyMarketStore()
  store.consultations = [{ id: 'c-1', title: '问题', status: 'completed' }]

  await store.selectConsultation('c-1')

  expect(api.getConsultation).toHaveBeenCalledWith('c-1')
  expect(store.selectedConsultation.answer).toBe('完整回答')
})
```

再增加详情失败测试，断言 `consultationsError` 或独立 `consultationDetailError` 有错误文案、现有列表不被清空。

- [ ] **Step 5: 实现 Store 的按需详情和成功刷新**

1. 导入 `getConsultation`。
2. state 中增加 `consultationDetailLoading: false`、`consultationDetailError: ''` 和 `consultationDetails: {}`。
3. `loadConsultations()` 仅保存摘要；默认选择第一项但不自动将摘要误作完整详情。
4. 将 `selectConsultation` 改为 `async`：先确认 ID 在 `consultations` 中，设置选中 ID；若 `consultationDetails[id]` 不存在，调用 `getConsultation(id)` 并存入缓存。API 异常记录详情错误后继续抛出。
5. getter `selectedConsultation` 应优先返回 `consultationDetails[selectedConsultationId]`，否则返回列表摘要。
6. `submitQuestion` 成功后将完整结果写入 `consultationDetails[completedRecord.id]`，以该记录替换临时项，并调用 `loadConsultations()` 刷新摘要列表；刷新失败不得覆盖已成功的完整结果。
7. 失败时保留临时记录为 `failed`，确保 `answer: ''` 与 `sourceData: null`，不生成静态成功回答。

处理并发时保持当前提交行为：单次提交期间 `submitting` 为真；不引入额外的轮询、重试或回退分支。

- [ ] **Step 6: 运行 API 与 Store 测试确认通过**

```bash
pnpm exec vitest -- run tests/policy-market-api.spec.js tests/policy-market-store.spec.js
```

预期：全部通过。

- [ ] **Step 7: 提交检查点（仅在用户明确授权后）**

```bash
git add agent-frontend/src/api/policyMarket.js agent-frontend/src/store/modules/policyMarket.js agent-frontend/tests/policy-market-api.spec.js agent-frontend/tests/policy-market-store.spec.js
git commit -m "feat: load persisted policy consultations in frontend"
```

## Task 6: 更新咨询结果展示和项目开发指南

**Files:**
- Modify: `agent-frontend/src/views/policy-market/components/ConsultationResult.vue`
- Modify: `agent-frontend/tests/policy-market-components.spec.js`
- Modify: `my_projects/investment-research-agent-项目开发指南.md`

- [ ] **Step 1: 编写结果组件的失败测试**

将成功态 fixture 从 `sourceScope` 改为：

```javascript
const completed = mount(ConsultationResult, {
  props: {
    consultation: {
      status: 'completed', title: '问题', answer: '回答',
      sourceData: {
        sources: ['https://example.test/source'],
        timeliness: { province: '宁夏', as_of: '2026-07', status: '已核验' },
        reminders: ['关注政策更新'],
      },
    },
  },
})
expect(completed.text()).toContain('https://example.test/source')
expect(completed.text()).toContain('宁夏')
expect(completed.text()).toContain('关注政策更新')
```

- [ ] **Step 2: 运行组件测试确认失败**

```bash
pnpm exec vitest -- run tests/policy-market-components.spec.js
```

预期：失败，组件仍仅读取 `sourceScope`。

- [ ] **Step 3: 用冻结的 sourceData 渲染结果元数据**

在 `ConsultationResult.vue` 保持现有 XC token 和无硬编码颜色约束。把 footer 内的 `sourceScope` 替换为来源、时效、提醒的条件展示：

```vue
<footer>
  <span v-if="consultation.sourceData?.sources?.length">
    来源：{{ consultation.sourceData.sources.join(' / ') }}
  </span>
  <span v-if="consultation.sourceData?.timeliness?.province">
    信息范围：{{ consultation.sourceData.timeliness.province }}
  </span>
  <span v-if="consultation.sourceData?.reminders?.length">
    提醒：{{ consultation.sourceData.reminders.join('；') }}
  </span>
  <span>状态：分析完成</span>
</footer>
```

不执行 URL 解析、富文本渲染或外链自动跳转；按照已有纯文本样式展示来源快照。

- [ ] **Step 4: 更新开发指南的模块现状与接口说明**

在 `my_projects/investment-research-agent-项目开发指南.md` 的 8.7 节，替换“当前 API 为模拟实现”的陈述，明确：

- 咨询通过 `/ir/policy-market/consultations` 的 POST、列表 GET 和详情 GET 对接。
- 后端以 `userId`/`username` Header 限制为当前用户，非本人资源为 404。
- 列表为摘要、详情按需加载；问答回答和 `sourceData` 是创建时冻结的数据库快照。
- 滚动资讯和概览仍沿用已有 `messages`、`messages/overview` 接口。

不在指南写入飞书凭据、LLM 密钥、数据库连接串或生产地址。

- [ ] **Step 5: 运行组件测试与前端构建**

```bash
pnpm exec vitest -- run tests/policy-market-components.spec.js tests/policy-market-api.spec.js tests/policy-market-store.spec.js tests/policy-market-page.spec.js
pnpm build
```

预期：测试全部通过，生产构建成功。

- [ ] **Step 6: 提交检查点（仅在用户明确授权后）**

```bash
git add agent-frontend/src/views/policy-market/components/ConsultationResult.vue agent-frontend/tests/policy-market-components.spec.js my_projects/investment-research-agent-项目开发指南.md
git commit -m "docs: document persisted policy consultations"
```

## Task 7: 执行全量回归与安全复核

**Files:**
- Verify only: 后端、前端及文档变更。

- [ ] **Step 1: 运行后端定向与全量测试**

在 `agent-backend/` 目录运行：

```bash
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['tests/unit/policy_market', 'tests/e2e/policy_market', '-q', '-o', 'asyncio_mode=auto']))"
.venv\Scripts\python.exe -c "import sys, pytest; sys.stdout = sys.stderr; raise SystemExit(pytest.main(['-q', '-o', 'asyncio_mode=auto']))"
```

预期：所有测试通过。如果存在与本变更无关的既有失败，记录完整失败输出、确认未由本变更引入，并停止在失败状态，不宣称完成。

- [ ] **Step 2: 运行全量前端测试与构建**

在 `agent-frontend/` 目录运行：

```bash
pnpm test
pnpm build
```

预期：测试和构建均成功。

- [ ] **Step 3: 审查变更与敏感信息泄漏**

在仓库根目录运行：

```bash
git diff --check
git diff -- agent-backend/tools/policy_ask.py agent-backend/app/core/config/settings.py agent-backend/configs/application.yml
```

预期：无空白错误；diff 中不包含任何密钥、Token、密码或真实数据库连接信息。核对新接口的每一个读取都带当前 `user_id`，并确认前端没有新增 `userId`/`username` 请求体字段。

- [ ] **Step 4: 提交最终变更（仅在用户明确授权后）**

若前述检查均通过且用户已授权 Git 写操作：

```bash
git status --short
git add agent-backend agent-frontend my_projects/investment-research-agent-项目开发指南.md docs/superpowers/plans/2026-07-24-policy-market-consultation-history.md
git commit -m "feat: persist policy market consultations"
```

预期：工作树仅保留用户有意未提交的文件；若有意外文件，先停止并向用户报告，不纳入提交。

## 计划自检

- **规格覆盖：** Task 1 覆盖表、ORM、DDL 与索引；Task 2 覆盖处理、成功冻结、失败标记和线程执行；Task 3 覆盖真实 `ask(question)` 适配与明文机密迁移；Task 4 覆盖创建/列表/详情 API、401/404/400 与用户隔离；Task 5 和 Task 6 覆盖 API、Store、组件和开发指南；Task 7 覆盖回归与敏感信息复核。
- **占位检查：** 计划不含 TODO/TBD；每项代码步骤给出具体类型、函数、路径和命令。
- **类型一致性：** 领域类型统一使用 `ConsultationRecord`、`ConsultationAnswer`；服务方法为 `create`、`list_for_user`、`get_for_user`；前端字段统一为 `sourceData`，后端存储为 `source_data`。
