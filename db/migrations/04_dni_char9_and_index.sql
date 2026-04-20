-- =========================================================================
-- MIGRATION 04 — Redimensionar DNI a CHAR(9) + índice compuesto
-- =========================================================================
-- Hay que drop FKs, resize columnas, re-add FKs (MariaDB no permite
-- redefinir columna participante en FK aunque se bajen FOREIGN_KEY_CHECKS).
-- =========================================================================

USE censo_animales;

SET FOREIGN_KEY_CHECKS=0;

-- Drop FKs que referencian DNI
ALTER TABLE `ANIMALES`              DROP FOREIGN KEY `fk_animales_propietario`;
ALTER TABLE `PROPIETARIO_DIRECCION` DROP FOREIGN KEY `fk_pd_propietario`;
ALTER TABLE `HISTORICO_MASCOTAS`    DROP FOREIGN KEY `fk_hist_propietario`;
ALTER TABLE `LICENCIAS`             DROP FOREIGN KEY `fk_lic_propietario`;

-- Resize columnas (referenciadoras)
ALTER TABLE `ANIMALES`              MODIFY `DNI_PROPIETARIO` CHAR(9) DEFAULT NULL;
ALTER TABLE `PROPIETARIO_DIRECCION` MODIFY `DNI`             CHAR(9) NOT NULL;
ALTER TABLE `HISTORICO_MASCOTAS`    MODIFY `DNI_PROPIETARIO` CHAR(9) DEFAULT NULL;
ALTER TABLE `LICENCIAS`             MODIFY `DNI_PROPIETARIO` CHAR(9) DEFAULT NULL;

-- Resize PK
ALTER TABLE `PROPIETARIOS` MODIFY `DNI` CHAR(9) NOT NULL;

-- Re-add FKs
ALTER TABLE `ANIMALES`
  ADD CONSTRAINT `fk_animales_propietario`
      FOREIGN KEY (`DNI_PROPIETARIO`) REFERENCES `PROPIETARIOS`(`DNI`)
      ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE `PROPIETARIO_DIRECCION`
  ADD CONSTRAINT `fk_pd_propietario`
      FOREIGN KEY (`DNI`) REFERENCES `PROPIETARIOS`(`DNI`)
      ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE `HISTORICO_MASCOTAS`
  ADD CONSTRAINT `fk_hist_propietario`
      FOREIGN KEY (`DNI_PROPIETARIO`) REFERENCES `PROPIETARIOS`(`DNI`)
      ON DELETE SET NULL ON UPDATE CASCADE;

ALTER TABLE `LICENCIAS`
  ADD CONSTRAINT `fk_lic_propietario`
      FOREIGN KEY (`DNI_PROPIETARIO`) REFERENCES `PROPIETARIOS`(`DNI`)
      ON DELETE CASCADE ON UPDATE CASCADE;

-- CP fijo
ALTER TABLE `PROPIETARIO_DIRECCION` MODIFY `CP` CHAR(5) DEFAULT NULL;

-- Índice compuesto (propietario, domicilio)
ALTER TABLE `ANIMALES` ADD INDEX `idx_anim_prop_dom` (`DNI_PROPIETARIO`, `ID_DOMICILIO`);

SET FOREIGN_KEY_CHECKS=1;
