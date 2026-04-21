-- ============================================================================
-- Migración 06: Índice en LICENCIAS.FECHA_EXPEDICION_LICENCIA
-- ============================================================================
-- Acelera la consulta de vencimiento de licencias PPP (RD 287/2002 art. 3.4:
-- renovación obligatoria cada 5 años). Idempotente.
-- ============================================================================

SET @db := DATABASE();

SET @idx_exists := (
  SELECT COUNT(*) FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = @db
    AND TABLE_NAME = 'LICENCIAS'
    AND INDEX_NAME = 'idx_licencias_fecha_exp'
);
SET @sql := IF(@idx_exists = 0,
  'CREATE INDEX idx_licencias_fecha_exp ON `LICENCIAS` (`FECHA_EXPEDICION_LICENCIA`)',
  'SELECT "idx_licencias_fecha_exp ya existe" AS info');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
