-- ============================================================================
-- Migración 13: columna FOTO en INCIDENCIAS
-- ============================================================================
-- Almacena la ruta relativa (servida por el frontend) de la foto adjunta a la
-- incidencia, por ejemplo: /fotos_incidencias/CHIP0001_20260427_120530.jpg
-- ============================================================================

ALTER TABLE `INCIDENCIAS`
  ADD COLUMN `FOTO` VARCHAR(255) DEFAULT NULL;
