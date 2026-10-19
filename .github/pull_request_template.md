## 变更说明

- 关联 Issue：
- Attempt ID：
- 候选 SHA：

## 约束确认

- [ ] 未修改平台身份、飞书权威计算、参数字典或历史快照不变量
- [ ] 未加入真实凭据，未连接真实外部服务或运行 `tests/db/`
- [ ] 未修改业务逻辑、依赖锁文件或现有测试断言
- [ ] 未部署、合并或重写历史

## 云端验证

| 检查 | 命令 | 计数/结果 | 退出码 |
| --- | --- | --- | --- |
| 后端单元测试 | `(cd agent-backend && .venv/bin/python -m pytest tests/unit -q)` |  |  |
| 前端测试 | `npm --prefix agent-frontend test` |  |  |
| 前端构建 | `npm --prefix agent-frontend run build` |  |  |

## 风险与人工审阅

- 已知差异/未执行项：
- 审阅重点：
