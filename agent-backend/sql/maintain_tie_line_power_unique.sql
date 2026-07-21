-- 对同一日期、线路名称和电压等级的历史重复记录保留最大 id。
DELETE older
FROM ir_tie_line_power AS older
JOIN ir_tie_line_power AS newer
  ON older.data_date = newer.data_date
 AND older.line_name = newer.line_name
 AND older.voltage_text = newer.voltage_text
 AND older.id < newer.id;

SET @index_exists := (
  SELECT COUNT(*)
  FROM information_schema.statistics
  WHERE table_schema = DATABASE()
    AND table_name = 'ir_tie_line_power'
    AND index_name = 'uk_ir_tie_line_power_date_name_voltage'
);
SET @sql := IF(
  @index_exists = 0,
  'ALTER TABLE ir_tie_line_power ADD UNIQUE INDEX uk_ir_tie_line_power_date_name_voltage (data_date, line_name, voltage_text)',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
