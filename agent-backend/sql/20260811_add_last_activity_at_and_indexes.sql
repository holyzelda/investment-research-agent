-- ============================================================
-- 历史列表性能优化：新增 last_activity_at 列 + 复合索引
-- 执行时间：MySQL 8 InnoDB，online DDL 不影响生产读写
-- ============================================================

-- 1. 新增 last_activity_at 列（可空，线上无锁）
ALTER TABLE ir_conversation
  ADD COLUMN last_activity_at DATETIME DEFAULT NULL
  COMMENT '最近活动时间：会话创建/新消息/新测算时更新，用于历史列表排序';

-- 2. 存量数据回填：last_activity_at = 该会话最大活动时间
UPDATE ir_conversation c
  JOIN (
    SELECT conversation_id, MAX(created_at) AS last_activity
    FROM ir_message_snapshot
    GROUP BY conversation_id
  ) m ON c.id = m.conversation_id
SET c.last_activity_at = m.last_activity;

-- 3. 没有消息的会话回填为 created_at
UPDATE ir_conversation
SET last_activity_at = created_at
WHERE last_activity_at IS NULL;

-- 4. 复合索引：覆盖 WHERE user_id=? AND deleted_at IS NULL ORDER BY last_activity_at DESC
ALTER TABLE ir_conversation
  ADD INDEX ix_ir_conv_user_deleted_activity (user_id, deleted_at, last_activity_at);

-- 5. 消息表复合索引：覆盖 MAX(created_at) WHERE conversation_id=? GROUP BY conversation_id
ALTER TABLE ir_message_snapshot
  ADD INDEX ix_ir_msg_conv_created (conversation_id, created_at);

-- 6. 任务表复合索引：覆盖 ORDER BY created_at DESC, id DESC WHERE conversation_id=? LIMIT 1
ALTER TABLE ir_calculation_task
  ADD INDEX ix_ir_task_conv_created_id (conversation_id, created_at, id);