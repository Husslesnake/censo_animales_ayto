"""Inserción masiva de prueba para comprobar límites de parámetros.

Inserta 500 propietarios y 500 animales marcados con prefijo TEST_ para
poder identificarlos y limpiarlos. Cada fila prueba valores en el borde
superior de cada VARCHAR/char declarado. Reporta errores y truncamientos.

Uso:
    python scripts/bulk_test_insert.py [limpiar]

Sin argumento: inserta.
Con "limpiar": borra las filas TEST_ y sale.
"""
from __future__ import annotations

import os
import sys
import time

import mysql.connector

CFG = {
    "host": os.environ.get("DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("DB_PORT", "3307")),
    "user": "root",
    "password": "123",
    "database": "censo_animales",
}


def _dni_sintetico(n: int) -> str:
    """DNI con letra correcta: 8 dígitos + letra de control."""
    letras = "TRWAGMYFPDXBNJZSQVHLCKE"
    numero = 10000000 + n
    return f"{numero:08d}{letras[numero % 23]}"


def limpiar(conn):
    """Elimina solo las filas insertadas por este script.

    DNIs de test: '99000001X' a '99000500X' (rango estricto, nunca 99999999X
    ni otros DNIs que puedan existir en producción).
    Chips de test: prefijo 'TEST_CHIP_'.
    """
    c = conn.cursor()
    # Hijos primero para respetar FKs
    c.execute("DELETE FROM BAJA_ANIMAL WHERE N_CHIP LIKE 'TEST\\_CHIP\\_%' ESCAPE '\\\\'")
    c.execute("DELETE FROM SEGUROS    WHERE N_CHIP LIKE 'TEST\\_CHIP\\_%' ESCAPE '\\\\'")
    c.execute("DELETE FROM CENSO      WHERE N_CHIP LIKE 'TEST\\_CHIP\\_%' ESCAPE '\\\\'")
    c.execute("DELETE FROM ANIMALES   WHERE N_CHIP LIKE 'TEST\\_CHIP\\_%' ESCAPE '\\\\'")
    # DNIs estrictamente entre 99000001 y 99000500
    c.execute(
        "DELETE FROM PROPIETARIOS WHERE DNI REGEXP '^990005[0-9]{2}[A-Z]$' "
        "OR DNI REGEXP '^9900[0-4][0-9]{2}[A-Z]$' OR DNI REGEXP '^99000[0-9]{2}[A-Z]$'"
    )
    conn.commit()
    print("[OK] filas TEST_ eliminadas")


def insertar(conn):
    N = 500
    c = conn.cursor()
    errores = []
    warnings = []
    t0 = time.time()

    # 500 propietarios con DNIs 99000001–99000500
    print(f"Insertando {N} propietarios…")
    for i in range(N):
        num = 99000000 + i + 1
        letras = "TRWAGMYFPDXBNJZSQVHLCKE"
        dni = f"{num:08d}{letras[num % 23]}"
        # Nombre de 50 chars exactos (borde superior)
        nombre = f"TEST_NOMBRE_{i:04d}_".ljust(50, "X")[:50]
        apellido = f"APELLIDO_{i:04d}".ljust(50, "Y")[:50]
        try:
            c.execute(
                "INSERT INTO PROPIETARIOS (DNI, NOMBRE, PRIMER_APELLIDO, SEGUNDO_APELLIDO, TELEFONO1) "
                "VALUES (%s, %s, %s, %s, %s)",
                (dni, nombre, apellido, "SEGUNDO", "612345678"),
            )
        except mysql.connector.Error as e:
            errores.append(("PROPIETARIOS", i, str(e)[:120]))
            break
    conn.commit()
    c.execute("SELECT COUNT(*) FROM PROPIETARIOS WHERE DNI LIKE '99______%'")
    n_prop = c.fetchone()[0]
    print(f"  -> {n_prop} insertados")

    # 500 animales TEST_CHIP_00001 … TEST_CHIP_00500 (15 chars exactos)
    # ANIMALES.N_CHIP es varchar(15). "TEST_CHIP_00001" = 15 chars justos.
    print(f"Insertando {N} animales (borde VARCHAR)…")
    especies = ["PERRO", "GATO", "HURON", "CONEJO", "CABALLO"]
    sexos = ["Macho", "Hembra"]
    for i in range(N):
        chip = f"TEST_CHIP_{i:05d}"  # 15 chars exactos
        dni_num = 99000000 + (i % N) + 1
        dni = f"{dni_num:08d}TRWAGMYFPDXBNJZSQVHLCKE"[: 9]
        letras = "TRWAGMYFPDXBNJZSQVHLCKE"
        dni = f"{dni_num:08d}{letras[dni_num % 23]}"
        nombre = f"TESTANIM_{i:04d}".ljust(50, "A")[:50]
        raza = "RAZA_BORDE_".ljust(80, "Z")[:80]
        color = "COLOR_" + "M" * 44  # 50 chars exactos
        try:
            c.execute(
                "INSERT INTO ANIMALES (N_CHIP, ESPECIE, RAZA, SEXO, NOMBRE, COLOR, "
                "ANIO_NACIMIENTO, ESTERILIZADO, PELIGROSO, DNI_PROPIETARIO) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    chip,
                    especies[i % len(especies)],
                    raza,
                    sexos[i % 2],
                    nombre,
                    color,
                    2000 + (i % 25),
                    i % 2,
                    1 if (i % 50 == 0) else 0,
                    dni,
                ),
            )
        except mysql.connector.Error as e:
            errores.append(("ANIMALES", i, str(e)[:120]))
            if len(errores) > 5:
                break
    conn.commit()
    c.execute("SELECT COUNT(*) FROM ANIMALES WHERE N_CHIP LIKE 'TEST_%'")
    n_anim = c.fetchone()[0]
    print(f"  -> {n_anim} insertados")

    # Verificar truncamientos
    c.execute(
        "SELECT COUNT(*) FROM ANIMALES WHERE N_CHIP LIKE 'TEST_%' "
        "AND (CHAR_LENGTH(NOMBRE) < 50 OR CHAR_LENGTH(COLOR) < 50 OR CHAR_LENGTH(RAZA) < 80)"
    )
    truncados = c.fetchone()[0]
    if truncados:
        warnings.append(f"{truncados} animales con campos truncados inesperadamente")

    # Probar inserción que DEBE fallar (DNI con letra incorrecta nunca, pero
    # aquí solo validamos largo): DNI > 9 chars
    print("Probando sobrepaso de CHAR(9) en DNI…")
    try:
        c.execute(
            "INSERT INTO PROPIETARIOS (DNI, NOMBRE, PRIMER_APELLIDO) VALUES (%s,%s,%s)",
            ("99999999XX", "TEST_OVER", "TEST"),
        )
        warnings.append("DNI de 10 chars aceptado (esperado: error Data too long)")
    except mysql.connector.Error as e:
        print(f"  -> rechazado correctamente: {str(e)[:100]}")

    # Probar N_CHIP > 15
    print("Probando sobrepaso de VARCHAR(15) en N_CHIP…")
    try:
        c.execute(
            "INSERT INTO ANIMALES (N_CHIP, ESPECIE) VALUES (%s,%s)",
            ("TEST_CHIP_TOOLONG_12345", "PERRO"),
        )
        warnings.append("N_CHIP de 23 chars aceptado (esperado: error)")
    except mysql.connector.Error as e:
        print(f"  -> rechazado correctamente: {str(e)[:100]}")

    # Probar ESPECIE NULL (actualmente permitido) con chip único
    print("Probando ANIMALES.ESPECIE = NULL…")
    try:
        c.execute(
            "INSERT INTO ANIMALES (N_CHIP, ESPECIE) VALUES (%s, NULL)",
            ("TEST_NULLESP_001",),
        )
        warnings.append("ANIMALES.ESPECIE NULL aceptado (candidato a NOT NULL)")
        c.execute("DELETE FROM ANIMALES WHERE N_CHIP = 'TEST_NULLESP_001'")
    except mysql.connector.Error as e:
        print(f"  -> ya rechazado: {e}")

    # Probar PROPIETARIOS.NOMBRE NULL
    print("Probando PROPIETARIOS.NOMBRE = NULL…")
    try:
        c.execute(
            "INSERT INTO PROPIETARIOS (DNI, NOMBRE, PRIMER_APELLIDO) VALUES (%s, NULL, %s)",
            ("99999001T", "X"),
        )
        warnings.append("PROPIETARIOS.NOMBRE NULL aceptado (candidato a NOT NULL)")
        c.execute("DELETE FROM PROPIETARIOS WHERE DNI = '99999001T'")
    except mysql.connector.Error as e:
        print(f"  -> ya rechazado: {e}")

    conn.commit()

    dt = time.time() - t0
    print(f"\n=== Resumen ({dt:.2f}s) ===")
    print(f"Propietarios TEST insertados: {n_prop}")
    print(f"Animales TEST insertados:     {n_anim}")
    print(f"Errores:   {len(errores)}")
    for t, i, e in errores[:10]:
        print(f"  - {t}[{i}]: {e}")
    print(f"Warnings:  {len(warnings)}")
    for w in warnings:
        print(f"  - {w}")


if __name__ == "__main__":
    conn = mysql.connector.connect(**CFG)
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "limpiar":
            limpiar(conn)
        else:
            insertar(conn)
    finally:
        conn.close()
