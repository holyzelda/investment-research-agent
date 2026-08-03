# 政策问答敏感配置外置设计

## 目标

将 `tools/policy_ask.py` 中硬编码的凭据、文档 Token 与可选第三方服务 Token 全部迁移至 `configs/application.yml` 的独立 `policy_ask` 配置节。脚本继续可被当前异步加载器独立导入，不依赖 FastAPI 运行时配置对象。

## 配置结构

在 `configs/application.yml` 新增：

- `policy_ask.feishu`：`app_id`、`app_secret`、`index_token`、`province_tokens` 与 `cross_province_token`。
- `policy_ask.llm`：`base_url`、`api_key`、`model`。
- `policy_ask.anysearch`：`api_key`。
- `policy_ask.base`：`token`、`table`。

其中飞书应用凭据、知识库索引 Token、三个省份 Token、LLM 服务地址/API Key/模型为必填配置；跨省页、AnySearch 与飞书 Base 维持可选，未配置时沿用既有禁用或降级逻辑。

## 加载行为

`policy_ask.py` 在模块导入时，根据脚本自身路径定位 `agent-backend/configs/application.yml`，使用 YAML 解析并读取 `policy_ask` 节。配置加载逻辑只负责读取、类型校验与错误提示，不引入 FastAPI 或应用层依赖。

配置文件不存在、YAML 根节点不是映射、必填项缺失或省份 Token 映射不完整时，应在导入阶段抛出包含配置路径和字段名的明确 `RuntimeError`，避免后续第三方调用中产生难定位错误。可选项为空字符串时按未配置处理。

## 代码边界

- 删除脚本内所有真实凭据与 Token 字面量。
- 保留 `PROVINCES`、`INDEX_TOKEN`、`LLM_*`、`ANYSEARCH_API_KEY`、`BASE_*` 等现有调用点，以最小改动将其赋值来源改为配置加载结果。
- 省份名、别名、提示词、缓存时长和业务关键字继续作为非敏感代码常量保留。
- 不改动政策问答的检索、LLM 调用、日志落库与异步预热流程。

## 测试与验证

新增针对配置加载函数的单元测试，覆盖：正常解析、缺少必填 LLM API Key、缺少省份 Token 与可选项为空时的行为。完成后运行该测试及现有政策问答加载器/执行器相关测试，确认 `tools.policy_ask` 的延迟导入机制未受影响。

## 非目标

本次不引入 Nacos、环境变量覆盖机制或 Secret 管理服务；不轮换现有凭据；不修改仓库中其他配置节或策略问答业务行为。
