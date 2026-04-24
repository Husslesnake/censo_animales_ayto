"""Inserta 25 propietarios reales con sus animales, seguros y vacunas en regla.

Cada propietario recibe entre 1 y 4 animales. Cada animal tiene:
  - FECHA_ULTIMA_VACUNACION_ANTIRRABICA dentro de los últimos 6 meses.
  - Una póliza en SEGUROS con FECHA_VENCIMIENTO_RC en el futuro.

DNIs: 85000001X–85000025X (rango libre al insertar este script).
Chips: 724900000000001–724900000000XXX (prefijo 724 ISO España).

No se usa SET FOREIGN_KEY_CHECKS=0; el orden de inserción respeta las FKs.

Uso:
    python scripts/seed_realistic_data.py
"""
from __future__ import annotations

import os
import random
from datetime import date, timedelta

import mysql.connector

CFG = {
    "host": os.environ.get("DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("DB_PORT", "3307")),
    "user": "root",
    "password": "123",
    "database": "censo_animales",
}

LETRAS_DNI = "TRWAGMYFPDXBNJZSQVHLCKE"

NOMBRES = [
    "Ana", "Carlos", "María", "Javier", "Lucía", "Pablo", "Elena", "David",
    "Sara", "Miguel", "Laura", "Jorge", "Carmen", "Alejandro", "Cristina",
    "Raúl", "Marta", "Fernando", "Patricia", "Sergio", "Isabel", "Rubén",
    "Noelia", "Álvaro", "Beatriz",
]
APELLIDOS = [
    "García", "Martínez", "López", "Sánchez", "Pérez", "González", "Rodríguez",
    "Fernández", "Gómez", "Díaz", "Jiménez", "Ruiz", "Moreno", "Álvarez",
    "Romero", "Navarro", "Torres", "Domínguez", "Vázquez", "Ramos",
    "Gil", "Serrano", "Molina", "Castro", "Ortiz",
]
ESPECIES = ["PERRO", "GATO", "HURON", "CONEJO"]
RAZAS = {
    "PERRO": ["Labrador", "Pastor Alemán", "Bulldog", "Mestizo", "Golden"],
    "GATO": ["Siamés", "Persa", "Común Europeo", "Maine Coon"],
    "HURON": ["Estándar", "Angora"],
    "CONEJO": ["Enano", "Belier", "Común"],
}
COLORES = ["Negro", "Blanco", "Marrón", "Atigrado", "Canela", "Gris", "Bicolor"]
SEXOS = ["Macho", "Hembra"]
COMPANIAS = ["Mapfre", "Mutua Madrileña", "Allianz", "AXA", "Catalana Occidente"]


def dni_valido(n: int) -> str:
    return f"{n:08d}{LETRAS_DNI[n % 23]}"


def main():
    rng = random.Random(42)  # determinista
    conn = mysql.connector.connect(**CFG)
    c = conn.cursor()

    c.execute("SELECT COALESCE(MAX(ID_SEGUROS), 0) FROM SEGUROS")
    next_seguro_id = c.fetchone()[0] + 1

    hoy = date.today()
    total_animales = 0
    total_seguros = 0

    for i in range(25):
        dni_num = 85000001 + i
        dni = dni_valido(dni_num)
        nombre = rng.choice(NOMBRES)
        ape1 = rng.choice(APELLIDOS)
        ape2 = rng.choice(APELLIDOS)
        tel = f"6{rng.randint(10000000, 99999999)}"
        email = f"{nombre.lower()}.{ape1.lower()}{i:02d}@example.com"

        c.execute(
            "INSERT INTO PROPIETARIOS (DNI, NOMBRE, PRIMER_APELLIDO, SEGUNDO_APELLIDO, TELEFONO1, EMAIL) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (dni, nombre, ape1, ape2, tel, email),
        )

        n_animales = rng.randint(1, 4)
        for j in range(n_animales):
            total_animales += 1
            chip = f"724900{total_animales:09d}"  # 15 chars exactos
            especie = rng.choice(ESPECIES)
            raza = rng.choice(RAZAS[especie])
            sexo = rng.choice(SEXOS)
            nombre_anim = rng.choice([
                "Luna", "Rocky", "Bella", "Max", "Coco", "Nala", "Toby",
                "Simba", "Lola", "Thor", "Kira", "Zeus",
            ])
            color = rng.choice(COLORES)
            anio = rng.randint(2015, 2024)
            dias_desde_vacuna = rng.randint(15, 180)  # 2 sem – 6 meses
            fecha_vacuna = hoy - timedelta(days=dias_desde_vacuna)
            peligroso = 1 if (especie == "PERRO" and rng.random() < 0.1) else 0
            esterilizado = 1 if rng.random() < 0.6 else 0

            c.execute(
                "INSERT INTO ANIMALES (N_CHIP, ESPECIE, RAZA, SEXO, NOMBRE, COLOR, "
                "ANIO_NACIMIENTO, FECHA_ULTIMA_VACUNACION_ANTIRRABICA, ESTERILIZADO, "
                "PELIGROSO, DNI_PROPIETARIO) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (chip, especie, raza, sexo, nombre_anim, color, anio,
                 fecha_vacuna, esterilizado, peligroso, dni),
            )

            compania = rng.choice(COMPANIAS)
            poliza = f"POL-{rng.randint(100000, 999999)}"
            vencimiento = hoy + timedelta(days=rng.randint(60, 365))
            c.execute(
                "INSERT INTO SEGUROS (ID_SEGUROS, N_CHIP, SEGURO_COMPANIA, SEGURO_POLIZA, "
                "FECHA_VENCIMIENTO_RC) VALUES (%s,%s,%s,%s,%s)",
                (next_seguro_id, chip, compania, poliza, vencimiento),
            )
            next_seguro_id += 1
            total_seguros += 1

    conn.commit()
    print(f"[OK] 25 propietarios insertados (DNIs {dni_valido(85000001)}–{dni_valido(85000025)})")
    print(f"[OK] {total_animales} animales insertados (chips 724900000000001–724900{total_animales:09d})")
    print(f"[OK] {total_seguros} pólizas de seguro insertadas, todas vigentes")
    conn.close()


if __name__ == "__main__":
    main()
