-- 河南城市区域双价格日最优结果表（增量发布，幂等执行）
CREATE TABLE IF NOT EXISTS ir_spot_daily_optimal_henan (
    province      VARCHAR(64)   NOT NULL,
    region        VARCHAR(64)   NOT NULL,
    business_date DATE          NOT NULL,
    k             TINYINT       NOT NULL,
    charge_sum    DECIMAL(20,6) NOT NULL,
    discharge_sum DECIMAL(20,6) NOT NULL,
    slot_count    INT           NOT NULL,
    PRIMARY KEY (province, region, k, business_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
