# 能力规格：calc-execution-engine（测算执行链路与快照）

> 来源：PRD US-1.4 + 状态机 §1.3.2。飞书副本权威测算、智能重试、7 类快照、版本记录。

## ADDED Requirements

### Requirement: 测算执行状态机

The system SHALL 以状态机执行测算：created → copying → writing → computing → reading → validating → snapshotting → completed，异常分支进入 failed/timeout。每次测算生成唯一 `task_id`，状态与飞书副本链接、会话ID、版本号持久化。

#### Scenario: 一次成功测算

- **GIVEN** 参数已备齐
- **WHEN** 后端复制副本、写入、等算、读取、校验、存快照
- **THEN** 任务状态流转至 completed，返回结果三模块数据，并写入一条版本记录

### Requirement: 副本策略

The system SHALL 每次**新测算复制一份新飞书副本**（独立文档隔离），**重试复用同一副本**（不重新复制）。

#### Scenario: 新测算新副本

- **WHEN** 用户发起一次全新测算
- **THEN** 系统复制出一份新的飞书副本文档用于本次计算

#### Scenario: 重试复用副本

- **WHEN** 某次测算触发智能重试
- **THEN** 重试复用同一副本，不产生新副本

### Requirement: 写入与等算完成判定

The system SHALL 生成 `request_id` 写入 `API_META`（request_id/参数hash/模板版本）与 `API_INPUT`（全部入参），随后轮询 `API_META` 状态字段与 request_id：仅当 `status=done` 且 request_id 一致时才读取 `API_OUTPUT`（防读旧值/串号）。轮询间隔默认 3s、总超时默认 10s，两参数经 Nacos 可配。

#### Scenario: 完成判定

- **GIVEN** 已写入 API_INPUT/API_META 且 request_id=R
- **WHEN** 轮询到 API_META 的 status=done 且回写 request_id=R
- **THEN** 系统读取 API_OUTPUT 并进入校验

#### Scenario: request_id 不匹配不读取

- **WHEN** 轮询到 status=done 但回写 request_id≠R
- **THEN** 系统不读取 API_OUTPUT，按可重试错误处理

### Requirement: 结果校验

The system SHALL 通过 request_id / 参数 hash 校验读到的 API_OUTPUT 确为本次计算产出，校验不通过（读到旧值）按失败处理。

#### Scenario: 校验通过

- **WHEN** 读到的结果 request_id 与参数 hash 均匹配本次任务
- **THEN** 校验通过并进入快照阶段

### Requirement: 智能重试

The system SHALL 区分错误类型执行重试：**可重试**（网络超时、飞书 5xx、限流 429、等算超时、request_id 不匹配）从头重试（复用同副本）最多 3 次，超限标记 failed 并提示"多次重试失败，请联系管理员"并展示 request_id；**不可重试**（鉴权 401/403、副本模板不存在、接口区结构损坏、参数校验非法）直接失败不重试并提示对应原因。

#### Scenario: 可重试错误自动恢复

- **GIVEN** 等算超时或网络抖动
- **WHEN** 触发重试
- **THEN** 自动重试（复用同副本，最多 3 次），成功则正常返回

#### Scenario: 超过重试上限

- **WHEN** 可重试错误连续发生超过 3 次
- **THEN** 任务标记 failed，返回"多次重试失败，请联系管理员"并携带 request_id

#### Scenario: 不可重试错误直接失败

- **GIVEN** 飞书鉴权失败 401
- **WHEN** 写入/读取被拒
- **THEN** 不重试，返回"请联系管理员"并记录 request_id

### Requirement: 7 类快照与脱离飞书可用

The system SHALL 每次测算独立保存 7 类快照（不覆盖，JSON 存 MySQL 库 `ir_agent`）：conversation、message_snapshot、calculation_task、input_snapshot、data_snapshot、feishu_io_snapshot（API_INPUT/OUTPUT/META 全量）、report_snapshot（含环形图/折线图底层数值，可直接渲染）。历史结果的展示数据源为 report_snapshot，**不依赖飞书副本**。

#### Scenario: 脱离飞书打开历史

- **GIVEN** 某次测算的飞书副本已被清理
- **WHEN** 用户查看该次测算/报告
- **THEN** 系统从 report_snapshot 正常展示图表与数值，不依赖飞书副本

### Requirement: 会话内版本记录

The system SHALL 在同一会话内为多次测算区分 V1/V2/V3…，右侧"报告管理"常驻列出版本，数据源为 report_snapshot；报告本体本阶段占位。

#### Scenario: 版本列表展示

- **WHEN** 同一会话内完成多次测算
- **THEN** 右侧版本列表按序展示 V1/V2/V3，最新版标记，点击可查看对应快照结果

### Requirement: 按运营期选择飞书模板

The system SHALL 在参数组装及受控覆盖完成后，根据最终冻结的 `operation_years` 选择复制来源：15 年使用 `template_token_15_years`，20 年使用 `template_token_20_years`。该值 SHALL 保留在任务响应和 `input_snapshot`；同一会话可混合 15 年与 20 年版本。复制后发生重试时 SHALL 复用同一副本，不重新选择模板或复制。

#### Scenario: 20 年模板

- **GIVEN** 最终冻结入参的 `operation_years=20`
- **WHEN** 发起测算
- **THEN** 系统使用 `template_token_20_years` 复制副本

#### Scenario: 版本混用

- **GIVEN** 同一会话的 V1 已按 15 年完成
- **WHEN** 用户以 `operation_years=20` 重新测算
- **THEN** V2 使用 20 年模板，且 V1/V2 的冻结入参分别保留对应运营期
