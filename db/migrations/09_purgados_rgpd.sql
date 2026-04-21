-- ============================================================================
-- Migración 09: Registro de purgados RGPD (minimización de datos)
-- ============================================================================
-- Crea PURGADOS_LOG para auditar qué filas se anonimizaron y cuándo.
-- La anonimización real la ejecuta la tarea programada _purgar_bajas_antiguas.
-- Idempotente.
-- ============================================================================

SET @db := DATABASE();

SET @t := (SELECT COUNT(*) FROM information_schema.TABLES
           WHERE TABLE_SCHEMA=@db AND TABLE_NAME='PURGADOS_LOG');
SET @sql := IF(@t=0, '
  CREATE TABLE `PURGADOS_LOG` (
    `ID`          INT(11)       NOT NULL AUTO_INCREMENT,
    `FECHA`       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `TABLA`       VARCHAR(64)   NOT NULL,
    `REFERENCIA`  VARCHAR(120)  NULL,
    `ACCION`      ENUM(''anonimizar'',''eliminar'') NOT NULL DEFAULT ''anonimizar'',
    `MOTIVO`      VARCHAR(200)  NOT NULL DEFAULT ''retencion_superada'',
    `DRY_RUN`     TINYINT(1)    NOT NULL DEFAULT 0,
    PRIMARY KEY (`ID`),
    KEY `idx_purg_fecha` (`FECHA`),
    KEY `idx_purg_tabla` (`TABLA`)
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
', 'SELECT "PURGADOS_LOG ya existe" AS info');
PREPARE st FROM @sql; EXECUTE st; DEALLOCATE PREPARE st;
