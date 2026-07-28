# 全国储能投资指数地图设计规格

- 日期：2026-07-28
- 状态：待评审
- 原型参考：`my_projects/reference_files/指数地图.png`
- 范围：全国指数地图的前后端只读查询与展示；数据库写入、数据同步及飞书接入均不在本期范围内。

## 1. 目标与边界

新增“全国指数地图”模块，将数据库内按期次沉淀的省级全国储能投资指数可视化为中国省级地图，并提供省份详情、全国汇总和榜单查看能力。

本期只支持一个指标，即“全国储能投资指数”。不增加指标切换、数据写入/导入、飞书读取或同步、报告导出、政策与市场页签、区域节点分析跳转的实际业务逻辑。

页面默认展示数据库中最新期次；用户可切换历史期次。每次期次切换应令地图、总览、榜单和右侧省份详情使用同一期数据。

## 2. 页面布局与交互

### 2.1 路由与导航

- 新增前端路由 `/index-map`，标题为“全国储能投资指数”。
- 启用左侧导航栏“全国指数地图”，点击后进入该路由；不再显示“待建”禁用态。
- 复用联络线地图的中国 GeoJSON、ECharts 生命周期封装、地图视图工具以及玄策（XC）设计 token；指数地图的状态、接口和组件保持独立，禁止通过“模式”混入联络线模块。

### 2.2 顶部区域

- 标题为“全国储能投资指数”，保留原型的说明性副标题。
- 原型中的“全国指数地图”页签为当前激活页；“政策与市场”“区域节点分析”保留视觉占位但不可访问。
- 增加期次/日期选择器，选项来自后端接口，默认选择最新期次。
- “导出洞察简报”保持占位交互并提示功能尚未开放，不生成或下载任何内容。

### 2.3 主地图

- 使用 ECharts 中国省级地图，根据省份的指数等级着色。
- 支持五种展示状态：
  - `S`：S 类·已开通；
  - `A`：A 类·已开通；
  - `B`：B 类·已开通；
  - `C`：C 类·待开通；
  - 无数据、未覆盖或非法等级：低强调底色，不纳入等级图例与等级统计。
- 地图保留等级图例，以及缩放、复位、全屏工具；使用 XC token 提供颜色，Canvas 使用 `xcVar()` 读取运行时 token，不硬编码颜色值。
- 悬停省份时，Tooltip 仅显示：省份名称、全国指数值、指数等级/全国排名、更新时间。
- 点击省份、点击任一榜单项，均选中该省并加载/切换右侧详情。选中省份在地图上具有明显高亮。
- 期次切换完成后：如原选中省份在新期仍有地图数据，则继续选中该省；否则选中该期领跑省份。随后加载对应详情。

### 2.4 全国总览和榜单

原型地图下方展示四张总览卡片：

1. 全国均值：全国指数均值及辅助说明；
2. 领跑省份：省名、指数和等级；
3. 已开通区域：省份数量及 S/A/B 分类数量；
4. 高潜待挖掘：C 类省份数量及辅助说明。

下方展示两张 Top 5 榜单，均可点击选省：

- 投资热力榜：展示排名、省份和指数分；
- 收益稳定榜：展示排名、省份和年化收益率。

### 2.5 右侧省份详情

选中省份后严格按原型布局呈现：

1. 省名、指数等级标签和定位/区域说明；
2. 指数总分（满分 100）和等级圆环；
3. 投资建议及年化收益率；
4. “归因分析·市场化成熟度”：成熟度等级、分析摘要，以及现货、调频、容量、辅助四项子分数；
5. “归因分析·因子贡献度”：现货价差、调频收益、容量电价、辅助服务四个贡献度进度条与增量值；
6. “装机结构·在运”：总装机规模、结构占比条；
7. 新能源、火电、储能三类技术路线装机卡片，展示占比、规模、构成/说明和增量；
8. 省级分析说明文案；
9. “查看省级区域节点分析”按钮，首期只提示功能尚未开放。

在尚未获得详情、详情为空、详情加载失败时，右侧面板独立展示对应状态，不清空地图和榜单。

## 3. API 契约

所有接口均为后端从数据库读取的数据，沿用 `{code, msg, data}` 响应壳；前端通过既有请求层请求，身份 Header 仍由全局请求层处理。

### 3.1 可选期次

`GET /ir/index-map/periods`

返回按时间倒序的期次数组：

```json
{
  "items": [
    {"period": "2026-07", "label": "2026年7月", "updatedAt": "2026-07-28T10:00:00+08:00"}
  ]
}
```

`period` 是全模块唯一的期次查询值；无期次时返回空数组。

### 3.2 期次概览

`GET /ir/index-map/overview?period={period}`

返回地图、省级悬停数据、总览和榜单，不携带完整省级归因详情：

```json
{
  "period": "2026-07",
  "updatedAt": "2026-07-28T10:00:00+08:00",
  "provinces": [
    {
      "provinceCode": "NMG",
      "provinceName": "蒙西",
      "mapName": "内蒙古",
      "indexScore": 95,
      "grade": "S",
      "opened": true,
      "rank": 1,
      "updatedAt": "2026-07-28T10:00:00+08:00"
    }
  ],
  "summary": {
    "nationalAverage": 68,
    "leader": {"provinceCode": "NMG", "provinceName": "蒙西", "indexScore": 95, "grade": "S"},
    "openedProvinceCount": 9,
    "openedGradeCounts": {"S": 1, "A": 5, "B": 3},
    "highPotentialCount": 6
  },
  "rankings": {
    "investmentHeat": [{"provinceCode": "NMG", "provinceName": "蒙西", "rank": 1, "indexScore": 95}],
    "returnStability": [{"provinceCode": "NMG", "provinceName": "蒙西", "rank": 1, "annualizedReturn": 8.9}]
  }
}
```

约束：

- `grade` 仅接受 `S`、`A`、`B`、`C`；其他值在前端按未覆盖显示。
- `provinceCode` 是选省和详情查询的稳定业务键；`mapName` 必须与中国 GeoJSON 的省级名称一致。
- `opened` 是页面统计和文案依据，S/A/B 必须为 `true`，C 必须为 `false`。
- 榜单最多返回 5 项，后端按目标指标降序和稳定业务键完成排序。

### 3.3 省份详情

`GET /ir/index-map/provinces/{provinceCode}?period={period}`

返回选中省份对应期次的完整详情：

```json
{
  "provinceCode": "NMG",
  "provinceName": "蒙西",
  "grade": "S",
  "regionDescription": "内蒙古·西部东送基地",
  "indexScore": 95,
  "investmentAdvice": "强烈推荐·立即布局",
  "annualizedReturn": 8.9,
  "maturity": {
    "grade": "A-",
    "summary": "现货、容量、调频三市场全线运行，价差形成机制清晰，机制稳定性高。",
    "scores": [
      {"key": "spot", "label": "现货", "score": 92},
      {"key": "frequencyRegulation", "label": "调频", "score": 78},
      {"key": "capacity", "label": "容量", "score": 85},
      {"key": "ancillary", "label": "辅助", "score": 70}
    ]
  },
  "factorContributions": [
    {"key": "spotSpread", "label": "现货价差", "value": 100, "delta": 23},
    {"key": "frequencyRevenue", "label": "调频收益", "value": 76, "delta": 14},
    {"key": "capacityPrice", "label": "容量电价", "value": 52, "delta": 8},
    {"key": "ancillaryService", "label": "辅助服务", "value": 36, "delta": 6}
  ],
  "installedStructure": {
    "totalGw": 208.0,
    "items": [
      {"key": "renewable", "label": "新能源", "share": 59, "capacityGw": 122.4, "description": "风电 64.8 · 光伏 57.6", "deltaText": "+31%"},
      {"key": "thermal", "label": "火电", "share": 38, "capacityGw": 78.2, "description": "燃煤/气电基础电源", "deltaText": "+4%"},
      {"key": "storage", "label": "储能", "share": 4, "capacityGw": 7.4, "description": "新型储能 · 电独立/共享", "deltaText": "+196%"}
    ]
  },
  "analysisText": "新能源装配容量持续高速增长，火电承担支撑性调节，储能渗透率形成空间。",
  "updatedAt": "2026-07-28T10:00:00+08:00"
}
```

数值为 `null` 时由前端采用统一空值展示“—”；不根据缺失字段伪造数值。接口找不到该期次或省份时返回项目既有的 404 业务语义。

## 4. 前后端实现边界

### 4.1 后端

新增独立的 `index_map` 模块，遵守 `interface → application → domain` 分层：

- `domain`：期次、省级概览和省份详情的不可变业务模型；不得依赖 FastAPI、SQLAlchemy 或外部 HTTP；
- `infrastructure.persistence`：ORM 和数据库查询实现；
- `application`：组装期次、概览和详情，处理期次存在性、排序与未找到情形；
- `interface`：路由、查询参数校验和 camelCase 序列化；
- `sql/ir_agent_schema.sql`：与 ORM 同步新增的数据库表及索引。

本期仅实现查询表/ORM/API，不实现向这些表写入的接口、定时任务、Excel 导入或任何飞书访问。

### 4.2 前端

新增以下独立单元：

- `src/api/indexMap.js`：三个只读 API 薄封装；
- `src/store/modules/indexMap.js`：期次、概览、选省、详情以及独立加载/失败状态；
- `src/views/index-map/index.vue`：页面编排与状态转发；
- 地图、期次控制、总览卡、榜单、右侧省份详情等聚焦组件；
- 指数等级展示映射和 ECharts option 构建文件。

Store 以 `requestVersion` 或等价的请求身份识别处理竞态：快速切换期次或连续点击省份后，过期请求不得覆盖当前 `activePeriod`、概览或详情。

## 5. 状态与错误处理

- 无期次：页面显示空态，不渲染虚构数据或右侧详情；
- 概览加载中：地图工作区展示加载态；
- 概览加载失败：地图工作区展示错误信息与重试；
- 详情加载中：仅右侧详情进入加载态；
- 详情加载失败：仅右侧详情展示重试，保留当前地图、统计和榜单；
- 某省无详情：右侧显示“该期次暂无省份详情”；
- 无效等级：按未覆盖显示，不参与等级统计，同时保留接口原始值以便诊断；
- 期次切换：完成概览加载后再决定有效选省并请求详情，避免地图和面板跨期混用。

## 6. 验收与测试

### 后端

- ORM 单测验证表名、字段类型、非空和索引约束；
- 应用服务单测覆盖最新期次、指定期次、榜单排序、无期次、无概览、无详情；
- 端到端端点测试使用 `httpx.ASGITransport + AsyncClient`，覆盖三个查询接口、业务 400 参数校验和 404 不存在资源；
- 每次 ORM 变更同步验证 `sql/ir_agent_schema.sql`。

### 前端

- Store 测试覆盖：默认最新期次、期次切换、保留/回退选省、地图和榜单选省、概览/详情重试、竞态保护；
- 组件测试覆盖：S/A/B/C/未覆盖映射、Tooltip 四项字段、地图点击、原型详情字段、空/加载/失败状态；
- 路由/导航测试覆盖：入口从禁用变为可访问并进入 `/index-map`；
- 运行全量前端测试和生产构建。

## 7. 明确不做

- 飞书数据读取、飞书同步、飞书写入；
- 数据库写入、数据导入、定时同步、数据治理；
- 多指标切换；
- 洞察简报导出；
- 政策与市场及区域节点分析页面的业务接入；
- 与联络线地图共享 Store、API、路由模式或条件分支。
