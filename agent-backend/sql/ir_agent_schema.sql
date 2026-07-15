-- 朱雀投研智能体 ir_agent 库 DDL（由 ORM 生成，MySQL 8 / InnoDB / utf8mb4）
-- 手动执行：在 internal-3-60.example.invalid 的 ir_agent 库运行本脚本建表。
-- schema 权威源为 app/modules/calculation/infrastructure/persistence/orm.py；本文件与其等价。

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

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
	FOREIGN KEY(conversation_id) REFERENCES ir_conversation (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE INDEX ix_ir_calculation_task_conversation_id ON ir_calculation_task (conversation_id);
CREATE INDEX ix_ir_calculation_task_request_id ON ir_calculation_task (request_id);

CREATE TABLE ir_message_snapshot (
	conversation_id BIGINT NOT NULL, 
	`role` VARCHAR(16) NOT NULL, 
	content TEXT NOT NULL, 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(conversation_id) REFERENCES ir_conversation (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE INDEX ix_ir_message_snapshot_conversation_id ON ir_message_snapshot (conversation_id);

CREATE TABLE ir_data_snapshot (
	task_id BIGINT NOT NULL, 
	payload JSON NOT NULL, 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(task_id) REFERENCES ir_calculation_task (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE INDEX ix_ir_data_snapshot_task_id ON ir_data_snapshot (task_id);

CREATE TABLE ir_feishu_io_snapshot (
	task_id BIGINT NOT NULL, 
	api_input JSON NOT NULL, 
	api_output JSON NOT NULL, 
	api_meta JSON NOT NULL, 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(task_id) REFERENCES ir_calculation_task (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE INDEX ix_ir_feishu_io_snapshot_task_id ON ir_feishu_io_snapshot (task_id);

CREATE TABLE ir_input_snapshot (
	task_id BIGINT NOT NULL, 
	payload JSON NOT NULL, 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(task_id) REFERENCES ir_calculation_task (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE INDEX ix_ir_input_snapshot_task_id ON ir_input_snapshot (task_id);

CREATE TABLE ir_report_snapshot (
	task_id BIGINT NOT NULL, 
	payload JSON NOT NULL, 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(task_id) REFERENCES ir_calculation_task (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE INDEX ix_ir_report_snapshot_task_id ON ir_report_snapshot (task_id);

SET FOREIGN_KEY_CHECKS = 1;
