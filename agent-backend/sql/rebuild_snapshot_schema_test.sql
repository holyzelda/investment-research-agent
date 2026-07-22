-- 仅用于配置的 ir_agent MySQL 测试库：重建测算/快照链路。
-- 不包含、不删除、不修改任一 ir_spot_* 表或其他无关表。

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS ir_report_snapshot;
DROP TABLE IF EXISTS ir_report_generation_task;
DROP TABLE IF EXISTS ir_calculation_result_snapshot;
DROP TABLE IF EXISTS ir_feishu_io_snapshot;
DROP TABLE IF EXISTS ir_data_snapshot;
DROP TABLE IF EXISTS ir_input_snapshot;
DROP TABLE IF EXISTS ir_message_snapshot;
DROP TABLE IF EXISTS ir_calculation_task;
DROP TABLE IF EXISTS ir_conversation;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE ir_conversation (
    user_id VARCHAR(64) NOT NULL,
    username VARCHAR(128) NOT NULL,
    title VARCHAR(255),
    deleted_at DATETIME,
    id BIGINT NOT NULL AUTO_INCREMENT,
    created_at DATETIME NOT NULL DEFAULT now(),
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE INDEX ix_ir_conversation_user_id ON ir_conversation (user_id);

CREATE TABLE ir_calculation_task (
    conversation_id BIGINT NOT NULL,
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
    conversation_id BIGINT NOT NULL,
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

CREATE TABLE ir_report_generation_task (
    task_id BIGINT NOT NULL,
    conversation_id BIGINT NOT NULL,
    user_id VARCHAR(64) NOT NULL,
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

CREATE TABLE ir_report_snapshot (
    report_id VARCHAR(64) NOT NULL,
    task_id BIGINT NOT NULL,
    conversation_id BIGINT NOT NULL,
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
