-- ============================================================================
-- Migración 08: Añade columna EMAIL a PROPIETARIOS (para recordatorios)
-- ============================================================================
-- Idempotente. La columna es opcional; si no hay email, se omite el envío.
-- ============================================================================

SET @db := DATABASE();

SET @col := (SELECT COUNT(*) FROM information_schema.COLUMNS
             WHERE TABLE_SCHEMA=@db AND TABLE_NAME='PROPIETARIOS' AND COLUMN_NAME='EMAIL');
SET @sql := IF(@col=0,
  'ALTER TABLE `PROPIETARIOS` ADD COLUMN `EMAIL` VARCHAR(120) NULL AFTER `TELEFONO2`',
  'SELECT "EMAIL ya existe" AS info');
PREPARE st FROM @sql; EXECUTE st; DEALLOCATE PREPARE st;

-- Registro de envíos (evita duplicar recordatorios el mismo día/aviso)
SET @t := (SELECT COUNT(*) FROM information_schema.TABLES
           WHERE TABLE_SCHEMA=@db AND TABLE_NAME='RECORDATORIOS_ENVIADOS');
SET @sql := IF(@t=0, '
  CREATE TABLE `RECORDATORIOS_ENVIADOS` (
    `ID`            INT(11)       NOT NULL AUTO_INCREMENT,
    `DNI`           VARCHAR(9)    NOT NULL,
    `EMAIL`         VARCHAR(120)  NOT NULL,
    `TIPO`          VARCHAR(40)   NOT NULL,
    `REFERENCIA`    VARCHAR(80)   NULL,
    `ENVIADO_EN`    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `EXITO`         TINYINT(1)    NOT NULL DEFAULT 1,
    `ERROR`         TEXT          NULL,
    PRIMARY KEY (`ID`),
    UNIQUE KEY `uniq_recordatorio_dia` (`DNI`, `TIPO`, `REFERENCIA`, `ENVIADO_EN`)
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
', 'SELECT "RECORDATORIOS_ENVIADOS ya existe" AS info');
PREPARE st FROM @sql; EXECUTE st; DEALLOCATE PREPARE st;
