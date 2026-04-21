-- ============================================================================
-- Migración 07: Ampliación de INCIDENCIAS (Ley 7/2023 art. 31)
-- ============================================================================
-- La tabla INCIDENCIAS ya existe con (ID, N_CHIP, TIPO, DESCRIPCION, FECHA,
-- ROL_AGENTE, AGENTE). Añade columnas para cumplir el registro de mordeduras,
-- gravedad, víctima y comunicación a Sanidad.
-- Idempotente: cada ALTER se envuelve en detección de existencia.
-- ============================================================================

SET @db := DATABASE();

-- Helper: añadir columna si no existe
DELIMITER //
DROP PROCEDURE IF EXISTS _add_col_if_missing //
CREATE PROCEDURE _add_col_if_missing(IN p_table VARCHAR(64), IN p_col VARCHAR(64), IN p_ddl TEXT)
BEGIN
  DECLARE v_exists INT DEFAULT 0;
  SELECT COUNT(*) INTO v_exists FROM information_schema.COLUMNS
   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = p_table AND COLUMN_NAME = p_col;
  IF v_exists = 0 THEN
    SET @s := CONCAT('ALTER TABLE `', p_table, '` ADD COLUMN ', p_ddl);
    PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;
  END IF;
END //
DELIMITER ;

CALL _add_col_if_missing('INCIDENCIAS', 'DNI_PROPIETARIO',    '`DNI_PROPIETARIO` VARCHAR(9) NULL');
CALL _add_col_if_missing('INCIDENCIAS', 'GRAVEDAD',           "`GRAVEDAD` ENUM('leve','moderada','grave','muy_grave') NOT NULL DEFAULT 'leve'");
CALL _add_col_if_missing('INCIDENCIAS', 'LUGAR',              '`LUGAR` VARCHAR(200) NULL');
CALL _add_col_if_missing('INCIDENCIAS', 'VICTIMA_NOMBRE',     '`VICTIMA_NOMBRE` VARCHAR(120) NULL');
CALL _add_col_if_missing('INCIDENCIAS', 'VICTIMA_CONTACTO',   '`VICTIMA_CONTACTO` VARCHAR(120) NULL');
CALL _add_col_if_missing('INCIDENCIAS', 'ATENDIDO_MEDICO',    '`ATENDIDO_MEDICO` TINYINT(1) NOT NULL DEFAULT 0');
CALL _add_col_if_missing('INCIDENCIAS', 'COMUNICADO_SANIDAD', '`COMUNICADO_SANIDAD` TINYINT(1) NOT NULL DEFAULT 0');
CALL _add_col_if_missing('INCIDENCIAS', 'FECHA_COMUNICACION', '`FECHA_COMUNICACION` DATETIME NULL');

DROP PROCEDURE IF EXISTS _add_col_if_missing;

-- Índices (idempotentes)
SET @idx := (SELECT COUNT(*) FROM information_schema.STATISTICS
             WHERE TABLE_SCHEMA=@db AND TABLE_NAME='INCIDENCIAS' AND INDEX_NAME='idx_incidencias_fecha');
SET @sql := IF(@idx=0, 'CREATE INDEX idx_incidencias_fecha ON `INCIDENCIAS` (`FECHA`)', 'SELECT 1');
PREPARE st FROM @sql; EXECUTE st; DEALLOCATE PREPARE st;

SET @idx := (SELECT COUNT(*) FROM information_schema.STATISTICS
             WHERE TABLE_SCHEMA=@db AND TABLE_NAME='INCIDENCIAS' AND INDEX_NAME='idx_incidencias_comunic');
SET @sql := IF(@idx=0, 'CREATE INDEX idx_incidencias_comunic ON `INCIDENCIAS` (`COMUNICADO_SANIDAD`, `FECHA`)', 'SELECT 1');
PREPARE st FROM @sql; EXECUTE st; DEALLOCATE PREPARE st;

SET @idx := (SELECT COUNT(*) FROM information_schema.STATISTICS
             WHERE TABLE_SCHEMA=@db AND TABLE_NAME='INCIDENCIAS' AND INDEX_NAME='idx_incidencias_dni');
SET @sql := IF(@idx=0, 'CREATE INDEX idx_incidencias_dni ON `INCIDENCIAS` (`DNI_PROPIETARIO`)', 'SELECT 1');
PREPARE st FROM @sql; EXECUTE st; DEALLOCATE PREPARE st;
