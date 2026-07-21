# 联络线功率导入接口设计

## 目标

为后续联络线功率数据写入提供单一 HTTP 接口：同一地址同时支持 Excel 文件上传和 JSON 宽表记录导入。接口以幂等覆盖方式维护“日期 + 名称 + 电压等级”业务唯一数据，统一返回写入统计。

## 范围

本次新增：

- `POST /ir/tie-lines/power/import`；
- `application/json` 与 `multipart/form-data` 两种请求解析；
- Excel 模板和 JSON 宽表记录校验；
- 按线路名称匹配 `ir_tie_line_map.id`；
- 单事务替换本次涉及业务键的旧记录；
- 存量数据去重（保留最大 `id`）及业务唯一索引；
- 应用服务、持久化模型、端点测试和依赖声明。

不新增：查询功率趋势 API、前端图表、异步任务、权限/RBAC、定时同步或数据清洗。

## 分层

采用 `interface → application → infrastructure`：

- `interface/router.py` 仅按 `Content-Type` 分派解析路径并返回统一响应壳；
- `interface` 的请求模型定义 JSON 结构；
- `application/power_import_service.py` 负责统一校验、线路名称匹配、删除旧记录、插入新记录和导入统计；
- `infrastructure/persistence/orm.py` 新增功率宽表 ORM，使 SQLAlchemy 能以合法 Python 属性映射数据库中的 `00:15` 等原始时段列；
- Excel 文件解析放在 interface 的独立模块中，输出与 JSON 相同的应用层导入记录。

## HTTP 契约

### 路由

```text
POST /ir/tie-lines/power/import
```

仅接受以下 `Content-Type`：

- `application/json`（允许 `; charset=utf-8` 等参数）；
- `multipart/form-data`。

其他媒体类型返回 HTTP 400 和统一响应壳。

### JSON 请求

```json
{
  "records": [
    {
      "dataDate": "2025-01-01",
      "lineName": "吉泉直流",
      "voltageText": "±1100kV",
      "powers": {
        "00:15": 8799,
        "00:30": 8798,
        "00:45": 8797,
        "01:00": 8905,
        "24:00": 9305
      }
    }
  ]
}
```

- `records` 必须非空；
- 每条记录必须提供 ISO 日期、非空线路名称、非空电压等级及 `powers`；
- `powers` 的键必须与固定 96 个时段精确一致，不得缺少或额外；
- 每个功率值为有限数值或 `null`；
- 请求体不接受 `lineId`，后端仅按名称匹配并写入；
- 同一请求内 `dataDate + lineName + voltageText` 不得重复。

### Excel 请求

```text
Content-Type: multipart/form-data
file: <.xlsx 文件>
```

- `file` 必填，文件名必须以 `.xlsx` 结尾；
- 工作簿必须包含“功率”工作表；
- 第一行表头必须精确为 `日期、名称、电压等级` 加固定的 96 个时段列；
- 至少一条数据行；
- 日期必须能转换为日期，名称/电压等级不得为空，功率单元格须为有限数值或空；
- 同一文件中不得含重复业务键。

Excel 与 JSON 都产出相同的应用层记录对象，因此后续数据校验和数据库写入路径完全一致。

### 成功响应

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "receivedCount": 14180,
    "deletedCount": 14180,
    "insertedCount": 14180,
    "matchedLineCount": 25
  }
}
```

## 写入行为

业务唯一键为：

```text
data_date + line_name + voltage_text
```

导入服务先在内存中完成全部输入校验和线路名称匹配。任何校验或匹配失败均返回 HTTP 400，且不会开始删除或插入。

校验通过后在单一数据库事务中：

1. 删除本次导入所有业务键对应的旧记录；
2. 插入本次全部新记录，其中 `line_id` 取匹配的静态线路 ID；
3. 统计删除和插入行数；
4. 请求成功时由会话提交，发生异常则回滚。

重复调用相同数据将先删后插，保证最终数据一致。接口不接受调用方指定的 `line_id`。

## 存量数据与数据库约束

在新增唯一索引前，对现有 `ir_tie_line_power` 执行一次去重：每个业务键仅保留最大 `id`，删除其余记录。

然后新增：

```sql
CREATE UNIQUE INDEX uk_ir_tie_line_power_date_name_voltage
ON ir_tie_line_power (data_date, line_name, voltage_text);
```

该约束与接口行为共同保证业务唯一性。数据库变更采用独立、可重复安全执行的维护脚本：删除重复数据使用自连接删除，唯一索引创建前由脚本通过 `information_schema.statistics` 检查索引是否存在。

## 错误处理

所有客户端输入问题均使用 `ValidationException`，即 HTTP 400 和 `{code, msg, data: null}`：

- 不支持的 Content-Type；
- 缺少文件、文件扩展名不正确、工作表或表头错误；
- 空记录集、日期/名称/电压等级/时段功率不合法；
- JSON 时段缺失或额外；
- 同请求重复业务键；
- 无法匹配的线路名称。

解析失败不暴露内部堆栈，仅返回可定位字段或行号的中文错误说明。数据库异常继续由统一全局处理器返回 500，并在事务边界回滚。

## ORM 与字段映射

功率宽表 ORM 的 `line_id` 为普通可空字段；`id` 是主键。各时段数据库列保持原始名称，Python 映射属性命名为 `power_0015_mw`、`power_0100_mw` 等。映射必须覆盖 96 列，含 `power_2400_mw` → `` `24:00` ``。

## 依赖与测试

后端依赖经 `agent-backend/requirements.txt` 管理：

- `openpyxl`：读取 `.xlsx`；
- `python-multipart`：解析 FastAPI 的 `multipart/form-data`。

端点测试仅使用 `httpx.ASGITransport + AsyncClient` 和内存 SQLite：

1. JSON 首次导入成功，写入 `line_id`、空功率和所有时段值；
2. JSON 重复导入同一业务键，旧记录被替换且总行数保持不变；
3. Excel 导入成功；
4. Excel 表头错误、JSON 缺时段/多时段、未知线路、同请求重复业务键和不支持媒体类型均返回 400 且不写入；
5. 断言 ORM 的 96 时段列映射、唯一索引定义和无外键；
6. 独立数据库维护脚本在有重复数据时保留最大 `id`，重复运行安全，并建立唯一索引。

## 文档同步

更新 `my_projects/联络线地图模块-功能与开发文档.md`：补充功率导入接口、业务唯一键、两种输入格式和当前无查询/图表能力的边界。
