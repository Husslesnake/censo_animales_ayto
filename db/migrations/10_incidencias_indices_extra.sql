-- ============================================================================
-- Migración 10: Índices adicionales en INCIDENCIAS (N_CHIP, TIPO)
-- ============================================================================
-- La migración 07 añadió índices en FECHA, (COMUNICADO_SANIDAD,FECHA) y
-- DNI_PROPIETARIO. Faltan N_CHIP y TIPO, que se usan como filtros y JOIN en
-- los endpoints /api/incidencias y /api/incidencias/exportar.
-- Idempotente.
-- ============================================================================

SET @db := DATABASE();

-- idx_incidencias_chip: filtros por chip y JOIN con ANIMALES
SET @idx := (SELECT COUNT(*) FROM information_schema.STATISTICS
             WHERE TABLE_SCHEMA=@db AND TABLE_NAME='INCIDENCIAS' AND INDEX_NAME='idx_incidencias_chip');
SET @sql := IF(@idx=0, 'CREATE INDEX idx_incidencias_chip ON `INCIDENCIAS` (`N_CHIP`)', 'SELECT 1');
PREPARE st FROM @sql; EXECUTE st; DEALLOCATE PREPARE st;

-- idx_incidencias_tipo: filtro por tipo de incidencia
SET @idx := (SELECT COUNT(*) FROM information_schema.STATISTICS
             WHERE TABLE_SCHEMA=@db AND TABLE_NAME='INCIDENCIAS' AND INDEX_NAME='idx_incidencias_tipo');
SET @sql := IF(@idx=0, 'CREATE INDEX idx_incidencias_tipo ON `INCIDENCIAS` (`TIPO`)', 'SELECT 1');
PREPARE st FROM @sql; EXECUTE st; DEALLOCATE PREPARE st;
