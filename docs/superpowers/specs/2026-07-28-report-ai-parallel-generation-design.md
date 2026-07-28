# 报告 AI 章节并行生成设计

## 背景与目标

正式报告生成会基于同一份冻结报告载荷分别生成五个 AI 章节。当前 `ReportGenerationService._generate_ai_sections()` 按规则顺序逐节 `await`，总延迟接近五次模型调用耗时之和。

本次目标是让五个章节并行调用中台模型池，并保持现有冻结数据边界、单节降级、历史报告只读快照等行为不变。初始并发上限配置为 5；后续若中台承压不足，可仅调整配置，无需改动业务逻辑。

## 现状与约束

- 五个章节上下文都只由 `build_report_payload()` 的冻结结构化数据独立构建。
- `investment_conclusion` 不读取前四节的 AI 正文，因此不存在章节间生成依赖。
- 每节调用都有独立的正文校验和 fallback，适合并行执行与失败隔离。
- `ModelPoolReportAiClient` 当前通过 `(app_id, user_id)` 查询 Token 缓存，但“查询缓存—申请 Token—写入缓存”跨越异步等待，不具备冷缓存下的 single-flight 保护。
- SQLAlchemy `AsyncSession` 不应被并发协程共享使用；章节协程只负责纯上下文构建和外部模型调用，不读写数据库。

## 方案选择

采用“有界并发 + Token single-flight”：

1. 五节任务通过有界异步并发执行，默认并发上限为 5。
2. Token 获取按 `(app_id, user_id)` 增加 single-flight 保护，冷缓存时只允许一个协程申请 Token。
3. 每节协程内部捕获异常并返回该节的 generated/fallback 结果，不让单节失败取消其他章节。
4. 全部任务完成后按 `AI_SECTION_RULES` 的原始顺序组装 `aiSections`，再由现有事务统一冻结报告。

不采用直接无保护的 `asyncio.gather()`，因为冷缓存时可能重复申请五次 Token。也不在报告应用服务中预取 Token，因为这会让应用层感知中台鉴权细节，破坏 `ReportAiPort` 边界。

## 组件设计

### 报告 AI 有界并发

在 `ReportGenerationService` 中引入报告 AI 并发上限，并由工厂从中台配置传入。`_generate_ai_sections()` 为每条规则创建一个独立协程；协程在调用 `ReportAiPort` 前进入共享 `asyncio.Semaphore`。

每节协程执行以下步骤：

1. 用冻结报告载荷构建该节 context。
2. 获取并发许可。
3. 调用 `generate_section()`。
4. 校验正文。
5. 返回 `(section_key, section_result)`。
6. 捕获任意单节异常并返回带稳定 `failureCode` 的 fallback。

默认并发上限为 5，因此当前五节会同时调用。配置改为 2 或 3 时，自动分批执行。

并发任务的完成顺序不参与持久化顺序；结果收集完成后按照规则列表顺序构造字典，保证报告快照和测试可复现。

### Token single-flight

在模型池客户端的 Token 获取路径增加按 Token key 隔离的 single-flight 任务。获取流程为：

1. 首次检查缓存，命中则直接返回。
2. 缓存未命中时，在一个短时持有的注册表锁内查询该 key 的在途任务。
3. 首个调用创建 Token 申请任务；同批其他调用取得并等待同一个任务。
4. 申请成功后写入缓存，所有等待者获得同一个 Token。
5. 任务结束后从在途任务表中移除；后续新请求仍可重新申请。

注册表锁只保护“查询或创建在途任务”的同步操作，不覆盖鉴权网络请求和模型调用，因此五个模型请求仍会并行。不同用户或不同应用使用不同 key，不共享在途任务。

Token 申请失败时，同批等待者共享同一个异常结果，不会由五个章节连续重复申请。失败任务会从表中清理，使后续新报告仍可正常重试。

## 配置

在 `MiddlePlatformConfig` 和 `configs/application.yml` 增加：

```yaml
middle_platform:
  report_model_concurrency: 5
```

并按现有优先级接入环境变量：

```text
IR_MIDDLE_PLATFORM_REPORT_MODEL_CONCURRENCY
```

配置必须为正整数。工厂创建 `ReportGenerationService` 时传入该值。默认值为 5，后续降为 2 或 3 时无需修改代码。

## 数据与进度流

```text
读取三份快照
  → 构建正式报告 payload
  → 提交 prepare 完成、ai active
  → 为五节构建独立任务
  → 最多五路并行调用模型
  → 每节独立 generated/fallback
  → 按规则顺序汇总 aiSections
  → 一次性写入 ReportSnapshotORM
  → 报告任务 completed
```

此次保留整体 AI 步骤的进度粒度：并行开始前为 active，全部章节结束后为 completed。章节协程不操作 ORM 或共享 `AsyncSession`，避免并发数据库会话问题。若后续需要展示“已完成 3/5”，应另行设计安全的独立会话或事件聚合机制，不纳入本次范围。

## 错误处理

- 单节超时、HTTP 错误、非法响应或正文校验失败，只降级该节。
- 一个章节失败不会取消其他并行章节。
- 保持现有稳定失败码：`ai_timeout`、`ai_transport_error`、`ai_upstream_rejected`、`ai_invalid_response`、`ai_output_validation_failed`。
- Token 申请失败由同批五节共享同一次失败，不重复冲击鉴权接口；各节仍各自冻结 fallback。
- 仅快照读取、报告构建或最终落库失败时，报告任务整体失败。
- 每节最多一次模型请求，不增加自动重试，避免重复计费。

## 测试设计

1. 使用可控的异步 Fake AI 客户端记录当前活跃调用数，断言并发配置为 5 时五节调用发生重叠，峰值为 5。
2. 将并发配置设为 2，断言峰值不超过 2，验证配置确实控制并发。
3. 冷 Token 缓存下并发调用五节，断言鉴权接口只调用一次、模型接口调用五次。
4. Token 已缓存时，断言鉴权接口不调用。
5. 模拟 Token 申请失败，断言同一批只申请一次且五节均按既有规则降级。
6. 模拟一节模型失败，断言其他四节成功且未被取消。
7. 让五节以不同顺序完成，断言最终 `aiSections` 仍按规则顺序组装。
8. 运行报告生成集成测试，确认报告只在五节全部结束后落库，历史读取不触发新模型调用。

## 非目标

- 不改变冻结上下文内容和提示词。
- 不改变模型名称、模型接口或认证协议。
- 不增加单节自动重试。
- 不增加逐章节数据库进度提交。
- 不并行操作 SQLAlchemy session。
- 不改变历史报告读取和 PDF 导出逻辑。
