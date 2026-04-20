-- =========================================================================
-- MIGRATION 01 — Rename columns containing special characters (Nº, Ñ, MINICIPIO)
-- =========================================================================
-- These characters break queries from drivers that don't send utf8 properly,
-- require backticks everywhere, and cause silent data corruption on some tools.
-- =========================================================================

USE censo_animales;

SET FOREIGN_KEY_CHECKS=0;

-- ------- ANIMALES -------
ALTER TABLE `ANIMALES`
  CHANGE `Nº_CHIP`                        `N_CHIP`                  VARCHAR(100) DEFAULT NULL,
  CHANGE `AÑO_DE_NACIMIENTO`              `ANIO_NACIMIENTO`         TEXT DEFAULT NULL,
  CHANGE `Nº_LICENCIA_ANIMALES_PELIGROSOS` `N_LICENCIA_ANIMALES_PELIGROSOS` VARCHAR(50) DEFAULT NULL,
  CHANGE `Nº_CITES`                       `N_CITES`                 TEXT DEFAULT NULL,
  CHANGE `SEGURO_COMPAÑIA`                `SEGURO_COMPANIA`         TEXT DEFAULT NULL,
  CHANGE `CERTIFICADO_ADIESTRADOR_Nº`     `N_CERTIFICADO_ADIESTRADOR` TEXT DEFAULT NULL,
  CHANGE `Nº_CENSO`                       `N_CENSO`                 TEXT DEFAULT NULL;

-- ------- CENSO -------
ALTER TABLE `CENSO`
  CHANGE `Nº_CHIP` `N_CHIP` VARCHAR(100) DEFAULT NULL;

-- ------- SEGUROS -------
ALTER TABLE `SEGUROS`
  CHANGE `Nº_CHIP` `N_CHIP` VARCHAR(100) DEFAULT NULL;

-- ------- BAJA_ANIMAL -------
ALTER TABLE `BAJA_ANIMAL`
  CHANGE `Nº_CHIP` `N_CHIP` VARCHAR(100) DEFAULT NULL,
  CHANGE `Nº_BAJA` `N_BAJA` TEXT DEFAULT NULL;

-- ------- ALTA_ANIMAL -------
ALTER TABLE `ALTA_ANIMAL`
  CHANGE `Nº_CHIP` `N_CHIP` VARCHAR(100) DEFAULT NULL,
  CHANGE `Nº_ALTA` `N_ALTA` TEXT DEFAULT NULL;

-- ------- HISTORICO_MASCOTAS -------
ALTER TABLE `HISTORICO_MASCOTAS`
  CHANGE `Nº_CHIP` `N_CHIP` VARCHAR(100) DEFAULT NULL;

-- ------- ANIMALES_PELIGROSOS -------
ALTER TABLE `ANIMALES_PELIGROSOS`
  CHANGE `Nº_CHIP`  `N_CHIP`  VARCHAR(100) DEFAULT NULL,
  CHANGE `Nº_CENSO` `N_CENSO` TEXT DEFAULT NULL;

-- ------- ADIESTRADORES -------
ALTER TABLE `ADIESTRADORES`
  CHANGE `Nº_CHIP` `N_CHIP` VARCHAR(100) DEFAULT NULL;

-- ------- PROPIETARIOS -------
-- MINICIPIO → MUNICIPIO (ortografía)
ALTER TABLE `PROPIETARIOS`
  CHANGE `MINICIPIO` `MUNICIPIO` TEXT DEFAULT NULL;

-- ------- PROPIETARIO_DIRECCION -------
ALTER TABLE `PROPIETARIO_DIRECCION`
  CHANGE `MINICIPIO` `MUNICIPIO` VARCHAR(100) DEFAULT NULL;

SET FOREIGN_KEY_CHECKS=1;
