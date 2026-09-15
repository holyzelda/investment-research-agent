-- 试用账号每日额度：按自然日保存用户三个功能的成功使用计数。
-- 手动执行：在目标 ir_agent 库运行本脚本。
-- 试用资格由统一平台 organization/users 的 roleKey 实时判断，本表只保存每日计数。
-- 关联 ORM：app/modules/trial_quota/infrastructure/persistence/orm.py

CREATE TABLE IF NOT EXISTS ir_trial_daily_usage (
    user_id VARCHAR(64) NOT NULL COMMENT '用户ID（统一平台 userId）',
    usage_date DATE NOT NULL COMMENT '计数所属自然日（Asia/Shanghai）',
    calculation_used INT NOT NULL DEFAULT 0 COMMENT '当日成功测算次数',
    report_used INT NOT NULL DEFAULT 0 COMMENT '当日成功报告份数',
    consultation_used INT NOT NULL DEFAULT 0 COMMENT '当日成功政策咨询次数',
    created_at DATETIME NOT NULL DEFAULT now(),
    updated_at DATETIME NOT NULL DEFAULT now() ON UPDATE now(),
    PRIMARY KEY (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 报告生成任务新增试用占用标记：后台异步失败时按标记回退当日报告额度。
-- 关联 ORM：app/modules/calculation/infrastructure/persistence/orm.py (ReportGenerationTaskORM)
ALTER TABLE ir_report_generation_task
    ADD COLUMN trial_quota_reserved TINYINT NOT NULL DEFAULT 0 COMMENT '本次报告生成任务是否已占用试用报告额度',
    ADD COLUMN trial_quota_usage_date DATE NULL COMMENT '试用报告额度占用所属自然日';
