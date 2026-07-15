-- 现货电价库·多循环 DP 预计算表（ir_agent 库，手动执行 DDL）
-- 逐日独立最优结果按 (区域/站点, 日期, K) 存原始价格和；测算时按滚动一年窗口求和 → 均价 → ×省份系数 → ÷1000。
-- K = floor(cycles × capacity/power × 4)，业务约束(cycles∈[1,2]步0.1，时长∈{2h,4h})下取值 ∈ {8..16,17,19,20,22,24,25,27,28,30,32}(19个)。
-- 系数不进表（存原始 元/MWh），查询时应用 → 支持系数热更新。

-- 省级：33 区域（宁夏/蒙西-全网…）。主键 (province,k,date) 便于按 (province,k) + 日期范围索引扫。
CREATE TABLE IF NOT EXISTS ir_spot_daily_optimal_province (
	province      VARCHAR(64)   NOT NULL,
	business_date DATE          NOT NULL,
	k             TINYINT       NOT NULL,
	charge_sum    DECIMAL(20,6) NOT NULL,   -- 当日入选充电槽电价之和(元/MWh 原始)
	discharge_sum DECIMAL(20,6) NOT NULL,   -- 当日入选放电槽电价之和
	slot_count    INT           NOT NULL,   -- 当日充=放 槽数
	PRIMARY KEY (province, k, business_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 节点级：现仅蒙西 492 站，一张表 + province 列。主键含 province 便于未来 PARTITION BY 平滑升级。
CREATE TABLE IF NOT EXISTS ir_spot_daily_optimal_node (
	province      VARCHAR(64)   NOT NULL,   -- 现统一"蒙西"
	station_name  VARCHAR(128)  NOT NULL,
	business_date DATE          NOT NULL,
	k             TINYINT       NOT NULL,
	charge_sum    DECIMAL(20,6) NOT NULL,
	discharge_sum DECIMAL(20,6) NOT NULL,
	slot_count    INT           NOT NULL,
	PRIMARY KEY (province, station_name, k, business_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 站点维表：前端下拉/搜索用。last_seen 判活跃。
CREATE TABLE IF NOT EXISTS ir_spot_station (
	province      VARCHAR(64)   NOT NULL,   -- 现统一"蒙西"
	station_name  VARCHAR(128)  NOT NULL,
	last_seen     DATE          NOT NULL,
	PRIMARY KEY (province, station_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
