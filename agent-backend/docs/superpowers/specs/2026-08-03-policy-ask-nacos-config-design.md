# 政策问答统一 Nacos 配置设计

## 目标

让政策问答模块与后端其他业务配置共用现有 `Settings` 和 Nacos 配置合并机制：本地调试读取 `configs/application.yml`；测试、生产部署在应用启动时分别从当前 Nacos profile 对应的配置中覆盖；Nacos 不可用时自动继续使用本地 YAML。

## 配置模型

在 `app/core/config/settings.py` 增加以下 Pydantic 配置模型：

- `PolicyAskFeishuConfig`：`app_id`、`app_secret`、`index_token`、`province_tokens`、`cross_province_token`。
- `PolicyAskLlmConfig`：`base_url`、`api_key`、`model`。
- `PolicyAskAnysearchConfig`：`api_key`。
- `PolicyAskBaseConfig`：`token`、`table`。
- `PolicyAskConfig`：组合上述子配置。

`Settings` 新增 `policy_ask` 字段。各字段从已深度合并的业务配置中获取，因此统一遵循现有优先级：Nacos 覆盖 > 本地 `application.yml` > Pydantic 默认值。此改造不增加环境变量覆盖项。

## 运行时数据流

1. 应用创建时，`Settings` 从本地 YAML 构建，因此本地调试可直接导入并使用政策问答脚本。
2. 生命周期启动时，`init_nacos_config()` 根据 `app.name` 和 `nacos.profile` 拉取对应 `{app.name}-{profile}.yml`，写入 Nacos 覆盖并执行 `reload_settings()`。
3. Nacos 加载完成后才调用 `start_policy_ask_warmup()`，延迟导入的 `tools.policy_ask` 通过 `get_settings().policy_ask` 取得已经合并完成的最终配置。
4. Nacos 未启用、不可达、无配置或配置格式无效时，现有降级逻辑清空远端覆盖并重建 Settings，政策问答脚本继续读取本地 YAML 配置。

测试与生产只需在各自 Nacos Data ID 中使用与本地完全相同的 `policy_ask` 层级；不需要在脚本中分支判断环境或访问 Nacos 缓存。

## 脚本边界

`tools/policy_ask.py` 删除 YAML 文件读取逻辑，改用 `get_settings().policy_ask`。脚本保留配置完整性校验：飞书必填凭据、知识库索引、三个省份 Token 和 LLM 三项配置为空时，在模块导入期抛出字段名明确的 `RuntimeError`。跨省 Token、AnySearch 和 Base 仍允许为空并保持禁用行为。

这使脚本依赖应用的统一配置入口，但不直接依赖 Nacos 客户端、Nacos 缓存或生命周期状态。

## 测试与验证

- 扩展 `tests/unit/test_settings.py`：断言 `policy_ask` 能从 YAML 构建，并在 `set_nacos_overrides()` 后由 Nacos 值覆盖。
- 调整政策问答配置测试：直接测试脚本对 `get_settings().policy_ask` 的映射与必填校验，不再验证脚本自行解析 YAML。
- 保留并运行策略问答加载器、执行器测试，确认延迟导入时序未变化。
- 冒烟验证本地 YAML 和模拟 Nacos 覆盖下的 `tools.policy_ask` 读取结果。

## 非目标

- 不修改 Nacos Data ID 命名、配置拉取和服务注册机制。
- 不新增环境变量、密钥管理服务或运行时热更新。
- 不修改策略问答的知识检索、第三方请求和日志写入行为。
