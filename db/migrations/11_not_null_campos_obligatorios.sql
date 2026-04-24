-- ============================================================================
-- Migración 11: NOT NULL en campos que deben tener dato por lógica de negocio
-- ============================================================================
-- Un animal chipado debe tener especie. Un propietario debe tener nombre y
-- primer apellido. Una baja siempre se refiere a un chip y una fecha.
-- Verificado previamente que existen 0 filas con NULL/'' en estas columnas.
-- No idempotente por sí solo: MODIFY es seguro de re-ejecutar (redefine la
-- columna con los mismos atributos).
-- ============================================================================

-- ANIMALES: especie obligatoria
ALTER TABLE `ANIMALES`
  MODIFY `ESPECIE` VARCHAR(50) NOT NULL;

-- PROPIETARIOS: nombre y primer apellido obligatorios
ALTER TABLE `PROPIETARIOS`
  MODIFY `NOMBRE`          VARCHAR(50) NOT NULL,
  MODIFY `PRIMER_APELLIDO` VARCHAR(50) NOT NULL;

-- BAJA_ANIMAL: chip y fecha obligatorios (una baja siempre es DE un chip CON fecha)
ALTER TABLE `BAJA_ANIMAL`
  MODIFY `N_CHIP` VARCHAR(15) NOT NULL,
  MODIFY `FECHA`  DATE         NOT NULL;
