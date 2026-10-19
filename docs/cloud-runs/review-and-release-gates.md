# ZHU-9 代码审查与部署边界（试点）

本文件记录 `holyzelda/investment-research-agent` 的受控交付规则。它只定义研发门禁和后续部署准入，不代表测试环境或生产环境已经建成。

## 当前生效的合并门禁

`main` 的 [Ruleset #25407955](https://github.com/holyzelda/investment-research-agent/rules/25407955) 要求拉取请求、至少一名独立审查者批准，以及以下五项来自 GitHub Actions 的成功检查：`frontend-test`、`frontend-build`、`backend-unit`、`mysql-integration`、`gitleaks-pull_request`。合并前候选分支必须基于最新 `main` 重新测试。新提交会使旧批准失效；强推、删除和绕过均被禁止。

`gitleaks-push` 只在推送到 `main` 后运行，用于合并后复核，不应作为拉取请求的必需检查。

## 审查与操作职责

| 对象 | 当前负责人 | 边界 |
| --- | --- | --- |
| CI 工作流、身份认证路径、数据库迁移与 DDL、CODEOWNERS | `7tyhk7rc84-source` | 在 `.github/CODEOWNERS` 中列出；启用“Require review from Code Owners”后，修改这些路径须由其批准。该账号已对 PR #12 的最终提交完成有效批准。 |
| PR 合并与仓库设置 | 仓库所有者 `holyzelda` | 只合并已经满足独立审查和所有必需检查的候选提交；保留候选 SHA、批准时间与合并 SHA。 |
| Codex | 无绕过和发布身份 | 可以准备变更、运行隔离检查和整理证据；不能替代人工批准或把 CI 成功解释为上线批准。 |
| staging / production 部署批准 | 待指定的人工负责人 | 在云账号、区域、域名、预算、网关和服务负责人确定前，不授予部署权限。 |

`CODEOWNERS` 本身也由 `7tyhk7rc84-source` 负责。关键路径的 PR 应由其他人提交；审查人不能批准自己的 PR。若该协作者不再可用，仓库所有者需先落实新的独立审查人并通过受控变更更新规则，不能绕过审查直接发布。

## 后续 GitHub Environments 设计

仓库目前没有 GitHub Environments，也没有部署工作流。创建环境前须完成 ZHU-10 的资源决策。

- `staging`：仅允许受保护的 `main` 提交部署；使用合成数据和专用测试凭据。可信测试网关负责认证并覆盖 `userId` / `username`，后端不直接暴露给浏览器。部署记录保存提交 SHA、镜像摘要、健康检查、认证/越权负向结果与回滚入口。
- `production`：与 staging 分离凭据和数据库；仅允许已通过门禁的 `main` 提交，由指定的人类发布审批人批准后手动触发。记录版本、变更、回滚方案和实际批准人。合并 PR 不自动部署生产。
- 任何真实飞书、中台、用户中心或 Nacos 凭据只在获准的受控环境中配置，不进入公开仓库、PR、日志或合成 CI。当前业务 CI 继续只使用一次性 MySQL 与本地模拟设置。

## 验证与完成条件

1. 用受控 PR 证明必需检查失败时不能合并；修复后确认检查重新运行。
2. 在所有必需检查成功但尚无独立批准时，证明仍不能合并。
3. 合并本文件及 `CODEOWNERS` 后启用代码所有者审查规则，并用后续关键路径 PR 验证其生效。
4. ZHU-10 的资源与发布审批人确定后，再创建环境、配置审批和进行真实部署负向验证。没有这一步不得宣称生产发布已受控验收。
