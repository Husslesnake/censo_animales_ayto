-- =========================================================================
-- MIGRATION 03 — PKs, FKs, colación, limpieza de huérfanos
-- =========================================================================

USE censo_animales;

SET FOREIGN_KEY_CHECKS=0;

-- -------------------------------------------------------------------------
-- 1) Limpiar huérfanos (filas en tablas hijas que referencian animales
--    inexistentes). Son 21 filas de datos de semilla sueltos.
-- -------------------------------------------------------------------------

-- CENSO, SEGUROS, HISTORICO_MASCOTAS, ADIESTRADORES pueden tener filas
-- con N_CHIP que no existe en ANIMALES.
DELETE c FROM CENSO c
 LEFT JOIN ANIMALES a ON a.N_CHIP = c.N_CHIP
 WHERE c.N_CHIP IS NOT NULL AND a.N_CHIP IS NULL;

DELETE s FROM SEGUROS s
 LEFT JOIN ANIMALES a ON a.N_CHIP = s.N_CHIP
 WHERE s.N_CHIP IS NOT NULL AND a.N_CHIP IS NULL;

DELETE h FROM HISTORICO_MASCOTAS h
 LEFT JOIN ANIMALES a ON a.N_CHIP = h.N_CHIP
 WHERE h.N_CHIP IS NOT NULL AND a.N_CHIP IS NULL;

DELETE x FROM ADIESTRADORES x
 LEFT JOIN ANIMALES a ON a.N_CHIP = x.N_CHIP
 WHERE x.N_CHIP IS NOT NULL AND a.N_CHIP IS NULL;

-- -------------------------------------------------------------------------
-- 2) Unificar colación de INCIDENCIAS para que FK/JOIN funcionen
-- -------------------------------------------------------------------------
ALTER TABLE `INCIDENCIAS`
  CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- 3) PK en ANIMALES sobre N_CHIP
-- -------------------------------------------------------------------------
-- N_CHIP ya es UNIQUE y no tiene NULLs; convertir a PK:
ALTER TABLE `ANIMALES` DROP INDEX `uq_ANIMALES_chip`;
ALTER TABLE `ANIMALES` MODIFY `N_CHIP` VARCHAR(15) NOT NULL;
ALTER TABLE `ANIMALES` ADD PRIMARY KEY (`N_CHIP`);

-- -------------------------------------------------------------------------
-- 4) Corregir tabla SEXO — la PK debe ser la CLAVE, no el nombre
-- -------------------------------------------------------------------------
ALTER TABLE `SEXO` DROP PRIMARY KEY;
ALTER TABLE `SEXO` DROP INDEX `uq_SEXO_clave`;
ALTER TABLE `SEXO`
  MODIFY `CLAVE` VARCHAR(10) NOT NULL,
  MODIFY `SEXO`  VARCHAR(50) NOT NULL;
ALTER TABLE `SEXO` ADD PRIMARY KEY (`CLAVE`);
ALTER TABLE `SEXO` ADD UNIQUE KEY `uq_SEXO_nombre` (`SEXO`);

-- -------------------------------------------------------------------------
-- 5) PROPIETARIO_DIRECCION — DNI NOT NULL (es lo que hace válida la fila)
-- -------------------------------------------------------------------------
-- Asegurarse de que no hay filas con DNI NULL
DELETE FROM PROPIETARIO_DIRECCION WHERE DNI IS NULL;
ALTER TABLE `PROPIETARIO_DIRECCION`
  MODIFY `DNI` VARCHAR(9) NOT NULL;

-- -------------------------------------------------------------------------
-- 6) Foreign keys
-- -------------------------------------------------------------------------
-- PROPIETARIO_DIRECCION.DNI → PROPIETARIOS.DNI
ALTER TABLE `PROPIETARIO_DIRECCION`
  ADD CONSTRAINT `fk_pd_propietario`
      FOREIGN KEY (`DNI`) REFERENCES `PROPIETARIOS`(`DNI`)
      ON DELETE CASCADE ON UPDATE CASCADE;

-- ANIMALES.DNI_PROPIETARIO → PROPIETARIOS.DNI  (RESTRICT: no borrar propietario con animales)
ALTER TABLE `ANIMALES`
  MODIFY `DNI_PROPIETARIO` VARCHAR(9) DEFAULT NULL,
  ADD CONSTRAINT `fk_animales_propietario`
      FOREIGN KEY (`DNI_PROPIETARIO`) REFERENCES `PROPIETARIOS`(`DNI`)
      ON DELETE RESTRICT ON UPDATE CASCADE;

-- ANIMALES.ID_DOMICILIO → PROPIETARIO_DIRECCION.CODIGO  (SET NULL si se borra dirección)
ALTER TABLE `ANIMALES`
  ADD CONSTRAINT `fk_animales_domicilio`
      FOREIGN KEY (`ID_DOMICILIO`) REFERENCES `PROPIETARIO_DIRECCION`(`CODIGO`)
      ON DELETE SET NULL ON UPDATE CASCADE;

-- ANIMALES.SEXO → SEXO.SEXO (mantener por nombre porque ya se inserta así)
-- (Omitido: necesitaría migrar datos existentes a CLAVE, lo dejamos como índice)

-- CENSO.N_CHIP → ANIMALES.N_CHIP
ALTER TABLE `CENSO`
  MODIFY `N_CHIP` VARCHAR(15) DEFAULT NULL,
  ADD CONSTRAINT `fk_censo_animal`
      FOREIGN KEY (`N_CHIP`) REFERENCES `ANIMALES`(`N_CHIP`)
      ON DELETE CASCADE ON UPDATE CASCADE;

-- SEGUROS.N_CHIP → ANIMALES.N_CHIP (UNIQUE: un seguro por animal)
ALTER TABLE `SEGUROS`
  MODIFY `N_CHIP` VARCHAR(15) DEFAULT NULL;
ALTER TABLE `SEGUROS`
  DROP INDEX `idx_seg_chip`;
ALTER TABLE `SEGUROS`
  ADD UNIQUE KEY `uq_seg_chip` (`N_CHIP`),
  ADD CONSTRAINT `fk_seguros_animal`
      FOREIGN KEY (`N_CHIP`) REFERENCES `ANIMALES`(`N_CHIP`)
      ON DELETE CASCADE ON UPDATE CASCADE;

-- BAJA_ANIMAL.N_CHIP → ANIMALES.N_CHIP
ALTER TABLE `BAJA_ANIMAL`
  MODIFY `N_CHIP` VARCHAR(15) DEFAULT NULL,
  ADD CONSTRAINT `fk_baja_animal`
      FOREIGN KEY (`N_CHIP`) REFERENCES `ANIMALES`(`N_CHIP`)
      ON DELETE CASCADE ON UPDATE CASCADE;

-- BAJA_ANIMAL.MOTIVO → MOTIVO_BAJA.CLAVE
ALTER TABLE `BAJA_ANIMAL`
  ADD CONSTRAINT `fk_baja_motivo`
      FOREIGN KEY (`MOTIVO`) REFERENCES `MOTIVO_BAJA`(`CLAVE`)
      ON DELETE RESTRICT ON UPDATE CASCADE;

-- ALTA_ANIMAL.N_CHIP → ANIMALES.N_CHIP
ALTER TABLE `ALTA_ANIMAL`
  MODIFY `N_CHIP` VARCHAR(15) DEFAULT NULL,
  ADD CONSTRAINT `fk_alta_animal`
      FOREIGN KEY (`N_CHIP`) REFERENCES `ANIMALES`(`N_CHIP`)
      ON DELETE CASCADE ON UPDATE CASCADE;

-- HISTORICO_MASCOTAS
ALTER TABLE `HISTORICO_MASCOTAS`
  MODIFY `N_CHIP` VARCHAR(15) DEFAULT NULL,
  MODIFY `DNI_PROPIETARIO` VARCHAR(9) DEFAULT NULL,
  ADD CONSTRAINT `fk_hist_animal`
      FOREIGN KEY (`N_CHIP`) REFERENCES `ANIMALES`(`N_CHIP`)
      ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_hist_estado`
      FOREIGN KEY (`ID_ESTADO`) REFERENCES `ESTADOS_HISTORICO`(`ID_ESTADO`)
      ON DELETE RESTRICT ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_hist_propietario`
      FOREIGN KEY (`DNI_PROPIETARIO`) REFERENCES `PROPIETARIOS`(`DNI`)
      ON DELETE SET NULL ON UPDATE CASCADE;

-- INCIDENCIAS.N_CHIP → ANIMALES.N_CHIP
ALTER TABLE `INCIDENCIAS`
  MODIFY `N_CHIP` VARCHAR(15) NOT NULL,
  ADD CONSTRAINT `fk_inc_animal`
      FOREIGN KEY (`N_CHIP`) REFERENCES `ANIMALES`(`N_CHIP`)
      ON DELETE CASCADE ON UPDATE CASCADE;

-- ANIMALES_PELIGROSOS
ALTER TABLE `ANIMALES_PELIGROSOS`
  MODIFY `N_CHIP` VARCHAR(15) DEFAULT NULL,
  ADD CONSTRAINT `fk_anipel_animal`
      FOREIGN KEY (`N_CHIP`) REFERENCES `ANIMALES`(`N_CHIP`)
      ON DELETE CASCADE ON UPDATE CASCADE;

-- ADIESTRADORES
ALTER TABLE `ADIESTRADORES`
  MODIFY `N_CHIP` VARCHAR(15) DEFAULT NULL,
  ADD CONSTRAINT `fk_adi_animal`
      FOREIGN KEY (`N_CHIP`) REFERENCES `ANIMALES`(`N_CHIP`)
      ON DELETE CASCADE ON UPDATE CASCADE;

-- LICENCIAS.DNI_PROPIETARIO → PROPIETARIOS.DNI
ALTER TABLE `LICENCIAS`
  MODIFY `DNI_PROPIETARIO` VARCHAR(9) DEFAULT NULL,
  ADD CONSTRAINT `fk_lic_propietario`
      FOREIGN KEY (`DNI_PROPIETARIO`) REFERENCES `PROPIETARIOS`(`DNI`)
      ON DELETE CASCADE ON UPDATE CASCADE;

-- ANIMALES.N_LICENCIA_ANIMALES_PELIGROSOS → LICENCIAS (si la tabla referencia licencias concretas)
ALTER TABLE `ANIMALES`
  ADD CONSTRAINT `fk_animales_licencia`
      FOREIGN KEY (`N_LICENCIA_ANIMALES_PELIGROSOS`)
      REFERENCES `LICENCIAS`(`N_LICENCIA_ANIMALES_PELIGROSOS`)
      ON DELETE SET NULL ON UPDATE CASCADE;

-- -------------------------------------------------------------------------
-- 7) Limpieza de columnas no usadas
-- -------------------------------------------------------------------------
-- PROPIETARIOS.CODIGO: no tiene sentido (el DNI ya es la clave)
ALTER TABLE `PROPIETARIOS` DROP COLUMN `CODIGO`;

-- BAJA_ANIMAL.BAJA: columna duplicada sin significado claro
ALTER TABLE `BAJA_ANIMAL` DROP COLUMN `BAJA`;

-- PROPIETARIOS.DOMICILIO/CP/MUNICIPIO: ahora viven en PROPIETARIO_DIRECCION
ALTER TABLE `PROPIETARIOS`
  DROP COLUMN `DOMICILIO`,
  DROP COLUMN `CP`,
  DROP COLUMN `MUNICIPIO`;

-- -------------------------------------------------------------------------
-- 8) Redimensionar DNI a CHAR(9) en todas las tablas (ahorra espacio, forma fija)
-- -------------------------------------------------------------------------
ALTER TABLE `PROPIETARIOS` MODIFY `DNI` CHAR(9) NOT NULL;
-- (las FKs ya creadas se ajustan en cascada gracias a ON UPDATE CASCADE)

-- -------------------------------------------------------------------------
-- 9) Índice compuesto para búsquedas por (propietario, domicilio)
-- -------------------------------------------------------------------------
ALTER TABLE `ANIMALES` ADD INDEX `idx_anim_prop_dom` (`DNI_PROPIETARIO`, `ID_DOMICILIO`);

SET FOREIGN_KEY_CHECKS=1;
