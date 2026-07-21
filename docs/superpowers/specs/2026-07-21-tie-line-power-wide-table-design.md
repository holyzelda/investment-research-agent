# 联络线功率宽表设计

## 目标

为联络线地图后续的功率趋势展示创建原始 Excel 功率数据的数据库表。本次范围仅包含 MySQL 手工 DDL 的建表定义，不包含 ORM、Excel 导入、查询 API、前端趋势图、数据清洗或真实数据库执行。

## 数据来源与建模方式

数据源为 `my_projects/reference_files/联络线-25条北交所.xlsx` 的“功率”工作表。其每行包含“日期、名称、电压等级”和 96 个 15 分钟功率时段列，覆盖 `00:15` 至 `24:00`。

采用与 Excel 一致的宽表，不将时段拆分为行。表名为 `ir_tie_line_power`。

## 表结构

- `id BIGINT AUTO_INCREMENT`：自增主键；`line_id` 不作为主键。
- `line_id BIGINT NULL`：后续按“名称 + 电压等级”匹配 `ir_tie_line_map.id` 后写入的可空关联值；不创建外键约束。
- `data_date DATE NOT NULL`：Excel“日期”。
- `line_name VARCHAR(128) NOT NULL`：Excel“名称”原值。
- `voltage_text VARCHAR(64) NOT NULL`：Excel“电压等级”原值。
- `` `00:15` `` 至 `` `24:00` ``：共 96 列，均为 `DECIMAL(12,3) NULL`，列名与 Excel 时段完全一致；每列使用“HH:MM 时段功率，单位：MW”的列备注。
- `created_at DATETIME NOT NULL DEFAULT now()`：建表记录创建时间。

所有时段功率列允许负值和空值，以保留原始功率方向与源表缺失值；`DECIMAL(12,3)` 兼容当前整数数据及未来小数精度。

## 索引

不创建唯一约束，以完整保留源 Excel 中可能重复的“日期 + 名称 + 电压等级”记录。创建下列普通索引：

- `ix_ir_tie_line_power_line_id_date (line_id, data_date)`
- `ix_ir_tie_line_power_name_voltage_date (line_name, voltage_text, data_date)`
- `ix_ir_tie_line_power_data_date (data_date)`

## 后续导入约定

后续编写 Excel 导入逻辑时，按“名称 + 电压等级”匹配 `ir_tie_line_map`；匹配成功写入 `line_id`，未匹配仍保留原始名称、电压等级和功率数据。重复行的保留、去重或覆盖规则不在本次建表范围内，必须在导入需求中另行明确。

## 实施与验证

实施时仅修改 `agent-backend/sql/ir_agent_schema.sql`，在 `ir_tie_line_map` 后新增等价的 MySQL 8 DDL、列备注与三个普通索引。使用脚本静态校验时段列数、顺序、类型、备注、索引和无外键约束。

不改动 ORM、API 路由、服务层、前端、数据库实际环境或 Excel 文件。
