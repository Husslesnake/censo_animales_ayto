-- ============================================================================
-- Migración 12: columna FOTO en ANIMALES
-- ============================================================================
-- Almacena la ruta relativa (servida por el frontend) de la foto del animal,
-- por ejemplo: /fotos_animales/CHIP0001.jpg
-- ============================================================================

ALTER TABLE `ANIMALES`
  ADD COLUMN `FOTO` VARCHAR(255) DEFAULT NULL AFTER `NOMBRE`;
