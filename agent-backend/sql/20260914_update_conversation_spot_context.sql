-- 会话上传电价上下文：保存价格用途和原始 96 点曲线。
-- 手动执行：在目标 ir_agent 库运行本脚本。
-- 适用前提：ir_conversation 已存在（conversation_id 外键依赖该表）。

CREATE TABLE IF NOT EXISTS ir_conversation_spot_context (
    id CHAR(36) NOT NULL,
    conversation_id CHAR(36),
    user_id VARCHAR(64) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'ready',
    context_token_hash VARCHAR(64) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_sha256 VARCHAR(64) NOT NULL,
    price_unit VARCHAR(16) NOT NULL DEFAULT 'CNY/MWh',
    price_mode VARCHAR(24) NOT NULL DEFAULT 'both'
        COMMENT '上传电价用途：both / charge_only / discharge_only',
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    valid_day_count INT NOT NULL,
    skipped_day_count INT NOT NULL DEFAULT 0,
    warnings JSON NOT NULL,
    k_results JSON NOT NULL,
    raw_prices JSON
        COMMENT '按自然日保存的原始 96 点电价曲线',
    algorithm_version VARCHAR(32) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT now(),
    updated_at DATETIME NOT NULL DEFAULT now() ON UPDATE now(),
    last_used_at DATETIME,
    expires_at DATETIME,
    PRIMARY KEY (id),
    UNIQUE KEY uq_ir_conv_spot_context_conversation (conversation_id),
    UNIQUE KEY uq_ir_conv_spot_context_token (context_token_hash),
    KEY ix_ir_conv_spot_context_user (user_id),
    KEY ix_ir_conv_spot_context_expires (expires_at),
    CONSTRAINT fk_ir_conv_spot_context_conversation
        FOREIGN KEY (conversation_id) REFERENCES ir_conversation (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
