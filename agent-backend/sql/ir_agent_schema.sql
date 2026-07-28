-- 朱雀投研智能体 ir_agent 库 DDL（MySQL 8 / InnoDB / utf8mb4）
-- 手动执行：在测试 ir_agent 库运行本脚本建表。
-- schema 权威源为 app/modules/calculation/infrastructure/persistence/orm.py；本文件与其等价。

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE ir_conversation (
    id CHAR(36) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    username VARCHAR(128) NOT NULL,
    title VARCHAR(255),
    deleted_at DATETIME,
    middle_platform_session_id VARCHAR(255),
    created_at DATETIME NOT NULL DEFAULT now(),
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE INDEX ix_ir_conversation_user_id ON ir_conversation (user_id);

CREATE TABLE consultation_records (
    id BIGINT NOT NULL AUTO_INCREMENT,
    user_id VARCHAR(64) NOT NULL,
    question TEXT NOT NULL,
    answer TEXT,
    province_code VARCHAR(20),
    topic VARCHAR(50),
    status VARCHAR(20) NOT NULL DEFAULT 'processing',
    source_data JSON,
    created_at DATETIME NOT NULL DEFAULT now(),
    answered_at DATETIME,
    updated_at DATETIME NOT NULL DEFAULT now() ON UPDATE now(),
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE INDEX idx_consultation_user_time ON consultation_records (user_id, created_at DESC);

CREATE TABLE ir_calculation_task (
    conversation_id CHAR(36) NOT NULL,
    version VARCHAR(16) NOT NULL,
    status VARCHAR(24) NOT NULL,
    request_id VARCHAR(64),
    param_hash VARCHAR(64),
    feishu_copy_url VARCHAR(512),
    error_code VARCHAR(64),
    error_message VARCHAR(512),
    retry_count BIGINT NOT NULL,
    id BIGINT NOT NULL AUTO_INCREMENT,
    created_at DATETIME NOT NULL DEFAULT now(),
    PRIMARY KEY (id),
    FOREIGN KEY (conversation_id) REFERENCES ir_conversation (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE INDEX ix_ir_calculation_task_conversation_id ON ir_calculation_task (conversation_id);
CREATE INDEX ix_ir_calculation_task_request_id ON ir_calculation_task (request_id);

CREATE TABLE ir_message_snapshot (
    conversation_id CHAR(36) NOT NULL,
    `role` VARCHAR(16) NOT NULL,
    content TEXT NOT NULL,
    message_type VARCHAR(32) NOT NULL DEFAULT 'text',
    payload JSON,
    id BIGINT NOT NULL AUTO_INCREMENT,
    created_at DATETIME NOT NULL DEFAULT now(),
    PRIMARY KEY (id),
    FOREIGN KEY (conversation_id) REFERENCES ir_conversation (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE INDEX ix_ir_message_snapshot_conversation_id ON ir_message_snapshot (conversation_id);

CREATE TABLE ir_data_snapshot (
    task_id BIGINT NOT NULL,
    payload JSON NOT NULL,
    id BIGINT NOT NULL AUTO_INCREMENT,
    created_at DATETIME NOT NULL DEFAULT now(),
    PRIMARY KEY (id),
    UNIQUE KEY uq_ir_data_snapshot_task_id (task_id),
    FOREIGN KEY (task_id) REFERENCES ir_calculation_task (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE ir_feishu_io_snapshot (
    task_id BIGINT NOT NULL,
    api_input JSON NOT NULL,
    api_output JSON NOT NULL,
    api_meta JSON NOT NULL,
    id BIGINT NOT NULL AUTO_INCREMENT,
    created_at DATETIME NOT NULL DEFAULT now(),
    PRIMARY KEY (id),
    UNIQUE KEY uq_ir_feishu_io_snapshot_task_id (task_id),
    FOREIGN KEY (task_id) REFERENCES ir_calculation_task (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE ir_input_snapshot (
    task_id BIGINT NOT NULL,
    payload JSON NOT NULL,
    id BIGINT NOT NULL AUTO_INCREMENT,
    created_at DATETIME NOT NULL DEFAULT now(),
    PRIMARY KEY (id),
    UNIQUE KEY uq_ir_input_snapshot_task_id (task_id),
    FOREIGN KEY (task_id) REFERENCES ir_calculation_task (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE ir_calculation_result_snapshot (
    task_id BIGINT NOT NULL,
    payload JSON NOT NULL,
    id BIGINT NOT NULL AUTO_INCREMENT,
    created_at DATETIME NOT NULL DEFAULT now(),
    PRIMARY KEY (id),
    UNIQUE KEY uq_ir_calculation_result_snapshot_task_id (task_id),
    FOREIGN KEY (task_id) REFERENCES ir_calculation_task (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE ir_tie_line_map (
	name VARCHAR(128) NOT NULL,
	start_point VARCHAR(128) NOT NULL,
	end_point VARCHAR(128) NOT NULL,
	length_text VARCHAR(64),
	voltage_text VARCHAR(64),
	start_region VARCHAR(64) NOT NULL,
	end_region VARCHAR(64) NOT NULL,
	start_longitude DECIMAL(10,6) NOT NULL,
	start_latitude DECIMAL(10,6) NOT NULL,
	end_longitude DECIMAL(10,6) NOT NULL,
	end_latitude DECIMAL(10,6) NOT NULL,
	rated_capacity_mw INT,
	operation_year INT,
	coordinate_basis VARCHAR(255),
	data_basis_note VARCHAR(512),
	source_note TEXT,
	id BIGINT NOT NULL AUTO_INCREMENT,
	created_at DATETIME NOT NULL DEFAULT now(),
	PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE INDEX ix_ir_tie_line_map_start_region ON ir_tie_line_map (start_region);
CREATE INDEX ix_ir_tie_line_map_end_region ON ir_tie_line_map (end_region);
CREATE INDEX ix_ir_tie_line_map_name ON ir_tie_line_map (name);

CREATE TABLE ir_index_map_period (
    period VARCHAR(32) NOT NULL,
    label VARCHAR(64) NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (period)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE INDEX ix_ir_index_map_period_updated_at ON ir_index_map_period (updated_at);

CREATE TABLE ir_index_map_province (
    id BIGINT NOT NULL AUTO_INCREMENT,
    period VARCHAR(32) NOT NULL,
    province_code VARCHAR(32) NOT NULL,
    province_name VARCHAR(64) NOT NULL,
    map_name VARCHAR(64) NOT NULL,
    index_score DECIMAL(8,2),
    grade VARCHAR(8),
    opened TINYINT(1) NOT NULL DEFAULT 0,
    `rank` INT,
    annualized_return DECIMAL(8,2),
    detail_payload JSON,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_ir_index_map_province_period
        FOREIGN KEY (period) REFERENCES ir_index_map_period (period),
    UNIQUE KEY uk_ir_index_map_province_period_code (period, province_code),
    KEY ix_ir_index_map_province_period_rank (period, `rank`),
    KEY ix_ir_index_map_province_period_score (period, index_score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE ir_tie_line_power (
    line_id BIGINT COMMENT '匹配 ir_tie_line_map 的线路 ID，无外键约束',
    data_date DATE NOT NULL COMMENT 'Excel 日期',
    line_name VARCHAR(128) NOT NULL COMMENT 'Excel 名称',
    voltage_text VARCHAR(64) NOT NULL COMMENT 'Excel 电压等级',
    `00:15` DECIMAL(12,3) COMMENT '00:15 时段功率，单位：MW',
    `00:30` DECIMAL(12,3) COMMENT '00:30 时段功率，单位：MW',
    `00:45` DECIMAL(12,3) COMMENT '00:45 时段功率，单位：MW',
    `01:00` DECIMAL(12,3) COMMENT '01:00 时段功率，单位：MW',
    `01:15` DECIMAL(12,3) COMMENT '01:15 时段功率，单位：MW',
    `01:30` DECIMAL(12,3) COMMENT '01:30 时段功率，单位：MW',
    `01:45` DECIMAL(12,3) COMMENT '01:45 时段功率，单位：MW',
    `02:00` DECIMAL(12,3) COMMENT '02:00 时段功率，单位：MW',
    `02:15` DECIMAL(12,3) COMMENT '02:15 时段功率，单位：MW',
    `02:30` DECIMAL(12,3) COMMENT '02:30 时段功率，单位：MW',
    `02:45` DECIMAL(12,3) COMMENT '02:45 时段功率，单位：MW',
    `03:00` DECIMAL(12,3) COMMENT '03:00 时段功率，单位：MW',
    `03:15` DECIMAL(12,3) COMMENT '03:15 时段功率，单位：MW',
    `03:30` DECIMAL(12,3) COMMENT '03:30 时段功率，单位：MW',
    `03:45` DECIMAL(12,3) COMMENT '03:45 时段功率，单位：MW',
    `04:00` DECIMAL(12,3) COMMENT '04:00 时段功率，单位：MW',
    `04:15` DECIMAL(12,3) COMMENT '04:15 时段功率，单位：MW',
    `04:30` DECIMAL(12,3) COMMENT '04:30 时段功率，单位：MW',
    `04:45` DECIMAL(12,3) COMMENT '04:45 时段功率，单位：MW',
    `05:00` DECIMAL(12,3) COMMENT '05:00 时段功率，单位：MW',
    `05:15` DECIMAL(12,3) COMMENT '05:15 时段功率，单位：MW',
    `05:30` DECIMAL(12,3) COMMENT '05:30 时段功率，单位：MW',
    `05:45` DECIMAL(12,3) COMMENT '05:45 时段功率，单位：MW',
    `06:00` DECIMAL(12,3) COMMENT '06:00 时段功率，单位：MW',
    `06:15` DECIMAL(12,3) COMMENT '06:15 时段功率，单位：MW',
    `06:30` DECIMAL(12,3) COMMENT '06:30 时段功率，单位：MW',
    `06:45` DECIMAL(12,3) COMMENT '06:45 时段功率，单位：MW',
    `07:00` DECIMAL(12,3) COMMENT '07:00 时段功率，单位：MW',
    `07:15` DECIMAL(12,3) COMMENT '07:15 时段功率，单位：MW',
    `07:30` DECIMAL(12,3) COMMENT '07:30 时段功率，单位：MW',
    `07:45` DECIMAL(12,3) COMMENT '07:45 时段功率，单位：MW',
    `08:00` DECIMAL(12,3) COMMENT '08:00 时段功率，单位：MW',
    `08:15` DECIMAL(12,3) COMMENT '08:15 时段功率，单位：MW',
    `08:30` DECIMAL(12,3) COMMENT '08:30 时段功率，单位：MW',
    `08:45` DECIMAL(12,3) COMMENT '08:45 时段功率，单位：MW',
    `09:00` DECIMAL(12,3) COMMENT '09:00 时段功率，单位：MW',
    `09:15` DECIMAL(12,3) COMMENT '09:15 时段功率，单位：MW',
    `09:30` DECIMAL(12,3) COMMENT '09:30 时段功率，单位：MW',
    `09:45` DECIMAL(12,3) COMMENT '09:45 时段功率，单位：MW',
    `10:00` DECIMAL(12,3) COMMENT '10:00 时段功率，单位：MW',
    `10:15` DECIMAL(12,3) COMMENT '10:15 时段功率，单位：MW',
    `10:30` DECIMAL(12,3) COMMENT '10:30 时段功率，单位：MW',
    `10:45` DECIMAL(12,3) COMMENT '10:45 时段功率，单位：MW',
    `11:00` DECIMAL(12,3) COMMENT '11:00 时段功率，单位：MW',
    `11:15` DECIMAL(12,3) COMMENT '11:15 时段功率，单位：MW',
    `11:30` DECIMAL(12,3) COMMENT '11:30 时段功率，单位：MW',
    `11:45` DECIMAL(12,3) COMMENT '11:45 时段功率，单位：MW',
    `12:00` DECIMAL(12,3) COMMENT '12:00 时段功率，单位：MW',
    `12:15` DECIMAL(12,3) COMMENT '12:15 时段功率，单位：MW',
    `12:30` DECIMAL(12,3) COMMENT '12:30 时段功率，单位：MW',
    `12:45` DECIMAL(12,3) COMMENT '12:45 时段功率，单位：MW',
    `13:00` DECIMAL(12,3) COMMENT '13:00 时段功率，单位：MW',
    `13:15` DECIMAL(12,3) COMMENT '13:15 时段功率，单位：MW',
    `13:30` DECIMAL(12,3) COMMENT '13:30 时段功率，单位：MW',
    `13:45` DECIMAL(12,3) COMMENT '13:45 时段功率，单位：MW',
    `14:00` DECIMAL(12,3) COMMENT '14:00 时段功率，单位：MW',
    `14:15` DECIMAL(12,3) COMMENT '14:15 时段功率，单位：MW',
    `14:30` DECIMAL(12,3) COMMENT '14:30 时段功率，单位：MW',
    `14:45` DECIMAL(12,3) COMMENT '14:45 时段功率，单位：MW',
    `15:00` DECIMAL(12,3) COMMENT '15:00 时段功率，单位：MW',
    `15:15` DECIMAL(12,3) COMMENT '15:15 时段功率，单位：MW',
    `15:30` DECIMAL(12,3) COMMENT '15:30 时段功率，单位：MW',
    `15:45` DECIMAL(12,3) COMMENT '15:45 时段功率，单位：MW',
    `16:00` DECIMAL(12,3) COMMENT '16:00 时段功率，单位：MW',
    `16:15` DECIMAL(12,3) COMMENT '16:15 时段功率，单位：MW',
    `16:30` DECIMAL(12,3) COMMENT '16:30 时段功率，单位：MW',
    `16:45` DECIMAL(12,3) COMMENT '16:45 时段功率，单位：MW',
    `17:00` DECIMAL(12,3) COMMENT '17:00 时段功率，单位：MW',
    `17:15` DECIMAL(12,3) COMMENT '17:15 时段功率，单位：MW',
    `17:30` DECIMAL(12,3) COMMENT '17:30 时段功率，单位：MW',
    `17:45` DECIMAL(12,3) COMMENT '17:45 时段功率，单位：MW',
    `18:00` DECIMAL(12,3) COMMENT '18:00 时段功率，单位：MW',
    `18:15` DECIMAL(12,3) COMMENT '18:15 时段功率，单位：MW',
    `18:30` DECIMAL(12,3) COMMENT '18:30 时段功率，单位：MW',
    `18:45` DECIMAL(12,3) COMMENT '18:45 时段功率，单位：MW',
    `19:00` DECIMAL(12,3) COMMENT '19:00 时段功率，单位：MW',
    `19:15` DECIMAL(12,3) COMMENT '19:15 时段功率，单位：MW',
    `19:30` DECIMAL(12,3) COMMENT '19:30 时段功率，单位：MW',
    `19:45` DECIMAL(12,3) COMMENT '19:45 时段功率，单位：MW',
    `20:00` DECIMAL(12,3) COMMENT '20:00 时段功率，单位：MW',
    `20:15` DECIMAL(12,3) COMMENT '20:15 时段功率，单位：MW',
    `20:30` DECIMAL(12,3) COMMENT '20:30 时段功率，单位：MW',
    `20:45` DECIMAL(12,3) COMMENT '20:45 时段功率，单位：MW',
    `21:00` DECIMAL(12,3) COMMENT '21:00 时段功率，单位：MW',
    `21:15` DECIMAL(12,3) COMMENT '21:15 时段功率，单位：MW',
    `21:30` DECIMAL(12,3) COMMENT '21:30 时段功率，单位：MW',
    `21:45` DECIMAL(12,3) COMMENT '21:45 时段功率，单位：MW',
    `22:00` DECIMAL(12,3) COMMENT '22:00 时段功率，单位：MW',
    `22:15` DECIMAL(12,3) COMMENT '22:15 时段功率，单位：MW',
    `22:30` DECIMAL(12,3) COMMENT '22:30 时段功率，单位：MW',
    `22:45` DECIMAL(12,3) COMMENT '22:45 时段功率，单位：MW',
    `23:00` DECIMAL(12,3) COMMENT '23:00 时段功率，单位：MW',
    `23:15` DECIMAL(12,3) COMMENT '23:15 时段功率，单位：MW',
    `23:30` DECIMAL(12,3) COMMENT '23:30 时段功率，单位：MW',
    `23:45` DECIMAL(12,3) COMMENT '23:45 时段功率，单位：MW',
    `24:00` DECIMAL(12,3) COMMENT '24:00 时段功率，单位：MW',
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '功率时序记录主键',
    created_at DATETIME NOT NULL DEFAULT now() COMMENT '记录创建时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_ir_tie_line_power_date_name_voltage (data_date, line_name, voltage_text)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='联络线功率宽表，时段列与 Excel 保持一致';
CREATE INDEX ix_ir_tie_line_power_line_id_date ON ir_tie_line_power (line_id, data_date);
CREATE INDEX ix_ir_tie_line_power_name_voltage_date ON ir_tie_line_power (line_name, voltage_text, data_date);
CREATE INDEX ix_ir_tie_line_power_data_date ON ir_tie_line_power (data_date);

CREATE TABLE ir_report_snapshot (
    report_id VARCHAR(64) NOT NULL,
    task_id BIGINT NOT NULL,
    conversation_id CHAR(36) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    schema_version SMALLINT NOT NULL DEFAULT 1,
    payload JSON NOT NULL,
    id BIGINT NOT NULL AUTO_INCREMENT,
    created_at DATETIME NOT NULL DEFAULT now(),
    PRIMARY KEY (id),
    UNIQUE KEY uq_ir_report_snapshot_report_id (report_id),
    UNIQUE KEY uq_ir_report_snapshot_task_id (task_id),
    FOREIGN KEY (task_id) REFERENCES ir_calculation_task (id),
    FOREIGN KEY (conversation_id) REFERENCES ir_conversation (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE INDEX ix_ir_report_snapshot_user_id ON ir_report_snapshot (user_id);
CREATE INDEX ix_ir_report_snapshot_conversation_created_at
    ON ir_report_snapshot (conversation_id, created_at);

SET FOREIGN_KEY_CHECKS = 1;


CREATE TABLE ir_report_generation_task (
    task_id BIGINT NOT NULL,
    conversation_id CHAR(36) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    username VARCHAR(128),
    status VARCHAR(16) NOT NULL DEFAULT 'generating',
    steps JSON NOT NULL,
    current_step VARCHAR(64),
    error_code VARCHAR(64),
    error_message VARCHAR(512),
    report_id VARCHAR(64),
    completed_at DATETIME,
    id BIGINT NOT NULL AUTO_INCREMENT,
    created_at DATETIME NOT NULL DEFAULT now(),
    PRIMARY KEY (id),
    UNIQUE KEY uq_ir_report_generation_task_task_id (task_id),
    FOREIGN KEY (task_id) REFERENCES ir_calculation_task (id),
    FOREIGN KEY (conversation_id) REFERENCES ir_conversation (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE INDEX ix_ir_report_generation_task_conversation_id ON ir_report_generation_task (conversation_id);
CREATE INDEX ix_ir_report_generation_task_user_id ON ir_report_generation_task (user_id);
CREATE INDEX ix_ir_report_generation_task_report_id ON ir_report_generation_task (report_id);

CREATE TABLE policy_market_scrolling_messages (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    title VARCHAR(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '标题',
    summary VARCHAR(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '简介',
    link_url VARCHAR(1000) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '跳转链接',
    province VARCHAR(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '省份',
    publish_time DATETIME DEFAULT NULL COMMENT '数据发布时间',
    expire_time DATETIME DEFAULT NULL COMMENT '过期/下线时间',
    status TINYINT NOT NULL DEFAULT 1 COMMENT '状态：0-禁用，1-启用',
    rating DECIMAL(3,2) DEFAULT 0.00 COMMENT '评分',
    sort_order INT NOT NULL DEFAULT 0 COMMENT '排序权重(数值越大越靠前)',
    tags VARCHAR(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '标签(逗号分隔或JSON)',
    extra_data JSON DEFAULT NULL COMMENT '扩展属性(JSON格式)',
    is_deleted TINYINT NOT NULL DEFAULT 0 COMMENT '逻辑删除：0-正常，1-已删除',
    created_by VARCHAR(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '创建人',
    updated_by VARCHAR(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '最后更新人',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    KEY idx_status_deleted_sort (is_deleted, status, sort_order DESC, rating DESC),
    KEY idx_province (province),
    KEY idx_expire_time (expire_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='政策与市场栏目-网页滚动播放信息表';