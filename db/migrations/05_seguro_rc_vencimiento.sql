-- ============================================================================
-- Migración 05: Vencimiento de Seguro de Responsabilidad Civil (Ley 7/2023 art. 30)
-- ============================================================================
-- Añade la fecha de vencimiento de la póliza RC a la tabla SEGUROS para poder
-- alertar al titular/ayuntamiento cuando el seguro está a punto de caducar.
--
-- Idempotente: detecta si la columna ya existe antes de añadirla.
-- ============================================================================

SET @db := DATABASE();

-- Añadir FECHA_VENCIMIENTO_RC si no existe
SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = @db
    AND TABLE_NAME = 'SEGUROS'
    AND COLUMN_NAME = 'FECHA_VENCIMIENTO_RC'
);
SET @sql := IF(@col_exists = 0,
  'ALTER TABLE `SEGUROS` ADD COLUMN `FECHA_VENCIMIENTO_RC` DATE NULL AFTER `SEGURO_POLIZA`',
  'SELECT "FECHA_VENCIMIENTO_RC ya existe" AS info');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Índice para consultas de vencimiento
SET @idx_exists := (
  SELECT COUNT(*) FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = @db
    AND TABLE_NAME = 'SEGUROS'
    AND INDEX_NAME = 'idx_seguros_vencimiento'
);
SET @sql := IF(@idx_exists = 0,
  'CREATE INDEX idx_seguros_vencimiento ON `SEGUROS` (`FECHA_VENCIMIENTO_RC`)',
  'SELECT "idx_seguros_vencimiento ya existe" AS info');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
