# 政策与市场模块市场脉搏数据库接入设计

## 目标

将政策与市场模块右侧“市场脉搏”的模拟资讯替换为 `policy_market_scrolling_messages` 表中的真实数据。覆盖滚动资讯横幅与资讯列表，移除“今日市场观察”区域。

## 范围

- 新增后端只读 `policy_market` 模块，遵循 `interface -> application -> domain -> infrastructure` 分层。
- 前端 `getMarketNews()` 由模拟异步数据改为后端请求。
- 保留现有 Store 的加载状态和页面初始化流程。
- 不涉及咨询记录、咨询统计、登录、内容管理、写入接口或数据库迁移机制。

## 数据读取规则

接口固定读取满足下列条件的记录：

- `is_deleted = 0`
- `status = 1`
- `expire_time IS NULL OR expire_time > 当前时间`

结果固定按以下顺序排列：

1. `sort_order DESC`
2. `rating DESC`
3. `publish_time DESC`
4. `id DESC`

第一条记录作为滚动资讯横幅内容；列表按同一顺序展示接口返回记录。无记录时横幅显示“暂无滚动资讯”，列表显示现有空状态。

## 接口契约

新增 `GET /ir/policy-market/messages`，响应保持统一壳 `{code, msg, data}`。

`data` 为数组，每条记录序列化为：

```json
{
  "id": 1,
  "title": "标题",
  "summary": "简介或 null",
  "linkUrl": "https://example.com/article",
  "province": "内蒙古",
  "publishTime": "2026-07-23T09:00:00",
  "tags": ["政策", "储能"]
}
```

- `tags` 按逗号分隔为数组；空值返回空数组。
- `extra_data` 不在此次接口中暴露。
- `linkUrl` 为空时前端不提供跳转行为；非空时在新窗口打开。

## 后端实现

- 在 `app/modules/policy_market/` 下建立接口、应用、领域和基础设施目录。
- 基础设施层定义 SQLAlchemy ORM，与既有手工 DDL 保持字段一致。
- 应用服务从 ORM 查询有效记录并装配领域值对象。
- 接口层依赖注入异步数据库会话，调用应用服务并序列化为 camelCase DTO。
- 将路由注册到应用入口。
- 将建表 DDL 增补到 `agent-backend/sql/ir_agent_schema.sql`，供新环境建库。

## 前端实现

- `src/api/policyMarket.js` 以请求层薄封装替换 `getMarketNews()` 的模拟数据。
- `src/store/modules/policyMarket.js` 继续以 `news`、`newsLoading`、`newsError` 管理读取结果，不改变初始化并发加载策略。
- `MarketPulse.vue`：
  - 横幅显示第一条资讯标题；
  - 列表展示标题、发布时间和标签；
  - 有 `linkUrl` 的条目以新窗口打开；
  - 移除详情弹窗入口和“今日市场观察”区域。
- 页面移除 `NewsDetailDialog`、选中资讯状态和相应事件处理。

## 异常与边界

- 数据库查询异常沿现有全局异常链路返回，前端继续使用 `newsError` 展示加载失败状态。
- 空数据是正常结果，返回空数组而非错误。
- 接口不接受查询参数，因此无需新增参数校验逻辑。

## 验证

- 后端：覆盖有效条件、过期/禁用/逻辑删除记录过滤、排序规则与接口响应壳。
- 前端：覆盖 API 请求路径与 DTO、Store 成功/失败状态、横幅取首条、空态、标签和外链行为，以及“今日市场观察”不再渲染。
- 执行后端定向 pytest、前端政策与市场相关 Vitest 用例及生产构建。
