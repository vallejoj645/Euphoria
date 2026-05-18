"""
Migración: agrega columnas de facturación electrónica DIAN.
Compatible con PostgreSQL y SQLite.
Ejecutar una sola vez: python migrate_factura_electronica.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app import app, db
from sqlalchemy import text


def es_postgres(conn):
    return 'postgresql' in str(conn.engine.url).lower() if hasattr(conn, 'engine') else False


def columna_existe(conn, tabla, columna):
    dialect = conn.engine.dialect.name
    if dialect == 'postgresql':
        resultado = conn.execute(
            text("""
                SELECT COUNT(*) FROM information_schema.columns
                WHERE table_name = :t AND column_name = :c
            """),
            {"t": tabla, "c": columna}
        )
    else:
        # SQLite
        resultado = conn.execute(
            text("SELECT COUNT(*) FROM pragma_table_info(:t) WHERE name=:c"),
            {"t": tabla, "c": columna}
        )
    return resultado.scalar() > 0


COLUMNAS_FACTURA = [
    ("es_electronica",         "BOOLEAN DEFAULT FALSE"),
    ("cufe",                   "VARCHAR(200)"),
    ("xml_content",            "TEXT"),
    ("qr_base64",              "TEXT"),
    ("cliente_tipo_documento", "VARCHAR(10) DEFAULT 'CC'"),
    ("cliente_email",          "VARCHAR(200)"),
    ("cliente_direccion",      "VARCHAR(300)"),
    ("cliente_ciudad",         "VARCHAR(100)"),
]

COLUMNAS_CONFIG = [
    ("numero_resolucion",   "VARCHAR(50)"),
    ("prefijo_facturacion", "VARCHAR(20) DEFAULT 'FACT'"),
    ("clave_tecnica",       "VARCHAR(200)"),
    ("software_id",         "VARCHAR(200)"),
    ("software_pin",        "VARCHAR(200)"),
    ("ambiente_dian",       "VARCHAR(1) DEFAULT '2'"),
    ("tipo_persona",        "VARCHAR(20) DEFAULT 'juridica'"),
    ("codigo_regimen",      "VARCHAR(20) DEFAULT 'O-13'"),
    ("departamento",        "VARCHAR(100)"),
    ("ciudad_nombre",       "VARCHAR(100)"),
]


def migrar():
    with app.app_context():
        with db.engine.connect() as conn:
            for col, tipo in COLUMNAS_FACTURA:
                if not columna_existe(conn, "factura", col):
                    conn.execute(text(f'ALTER TABLE factura ADD COLUMN {col} {tipo}'))
                    conn.commit()
                    print(f"  + factura.{col}")
                else:
                    print(f"  = factura.{col} ya existe")

            for col, tipo in COLUMNAS_CONFIG:
                if not columna_existe(conn, "configuracion_restaurante", col):
                    conn.execute(text(f'ALTER TABLE configuracion_restaurante ADD COLUMN {col} {tipo}'))
                    conn.commit()
                    print(f"  + configuracion_restaurante.{col}")
                else:
                    print(f"  = configuracion_restaurante.{col} ya existe")

    print("\nMigración completada.")


if __name__ == "__main__":
    migrar()
