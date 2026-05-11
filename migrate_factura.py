"""
Script completo de migración para el modelo Factura
1. Agrega campo fecha_emision
2. Hace sesion_id nullable
Ejecutar: python migrate_factura_complete.py
"""

import sqlite3
import os
from datetime import datetime

def migrate_factura_complete():
    """
    Migración completa de la tabla factura:
    - Agrega fecha_emision (con DEFAULT CURRENT_TIMESTAMP)
    - Hace sesion_id nullable
    """
    
    db_path = 'restaurante.db'
    
    if not os.path.exists(db_path):
        print(f"❌ Error: No se encuentra la base de datos en {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🔄 Iniciando migración completa de tabla factura...")
    
    try:
        # Crear backup
        print("📦 Creando backup...")
        cursor.execute("DROP TABLE IF EXISTS factura_backup")
        cursor.execute("CREATE TABLE factura_backup AS SELECT * FROM factura")
        
        # Contar facturas
        cursor.execute("SELECT COUNT(*) FROM factura")
        count = cursor.fetchone()[0]
        print(f"📊 Facturas existentes: {count}")
        
        # Eliminar tabla antigua
        print("🗑️  Eliminando tabla antigua...")
        cursor.execute("DROP TABLE factura")
        
        # Crear nueva tabla con TODOS los campos correctos
        print("🏗️  Creando nueva tabla con fecha_emision y sesion_id nullable...")
        cursor.execute("""
            CREATE TABLE factura (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_consecutivo VARCHAR(50) UNIQUE NOT NULL,
                sesion_id INTEGER,
                subtotal FLOAT DEFAULT 0,
                iva FLOAT DEFAULT 0,
                propina FLOAT DEFAULT 0,
                total FLOAT DEFAULT 0,
                metodo_pago VARCHAR(50) DEFAULT 'efectivo',
                desglose_pago TEXT,
                cliente_nombre VARCHAR(200),
                cliente_documento VARCHAR(50),
                notas TEXT,
                estado_pago VARCHAR(20) DEFAULT 'pagada',
                fecha_vencimiento DATE,
                fecha_pago_real DATETIME,
                saldo_pendiente FLOAT DEFAULT 0,
                fecha_emision DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sesion_id) REFERENCES sesion(id)
            )
        """)
        
        # Copiar datos del backup
        if count > 0:
            print("📋 Copiando facturas existentes...")
            cursor.execute("""
                INSERT INTO factura (
                    id, numero_consecutivo, sesion_id, subtotal, iva, propina, 
                    total, metodo_pago, desglose_pago, cliente_nombre, 
                    cliente_documento, notas, estado_pago, fecha_vencimiento,
                    fecha_pago_real, saldo_pendiente, fecha_emision
                )
                SELECT 
                    id, numero_consecutivo, sesion_id, subtotal, iva, propina,
                    total, metodo_pago, desglose_pago, cliente_nombre,
                    cliente_documento, notas, estado_pago, fecha_vencimiento,
                    fecha_pago_real, saldo_pendiente,
                    COALESCE(fecha_pago_real, CURRENT_TIMESTAMP) as fecha_emision
                FROM factura_backup
            """)
        
        # Eliminar backup
        print("🧹 Limpiando backup...")
        cursor.execute("DROP TABLE factura_backup")
        
        # Commit
        conn.commit()
        
        # Verificar
        cursor.execute("SELECT COUNT(*) FROM factura")
        new_count = cursor.fetchone()[0]
        
        # Verificar estructura
        cursor.execute("PRAGMA table_info(factura)")
        columns = cursor.fetchall()
        
        print("\n✅ Migración completada exitosamente")
        print(f"✓ Facturas migradas: {new_count}/{count}")
        print("✓ Columna sesion_id: NULLABLE")
        print("✓ Columna fecha_emision: AGREGADA")
        
        print("\n📋 Estructura actualizada:")
        for col in columns:
            print(f"   - {col[1]}: {col[2]}")
        
        print("\n🎉 Ahora puedes facturar domicilios sin problemas\n")
        
    except Exception as e:
        print(f"\n❌ Error durante la migración: {str(e)}")
        conn.rollback()
        
        # Intentar restaurar backup
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='factura_backup'")
            if cursor.fetchone():
                print("🔄 Restaurando backup...")
                cursor.execute("DROP TABLE IF EXISTS factura")
                cursor.execute("ALTER TABLE factura_backup RENAME TO factura")
                conn.commit()
                print("✓ Backup restaurado")
        except:
            print("⚠️  No se pudo restaurar el backup automáticamente")
    
    finally:
        conn.close()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  MIGRACIÓN COMPLETA: Factura")
    print("  - fecha_emision (nuevo campo)")
    print("  - sesion_id nullable (para domicilios)")
    print("="*60 + "\n")
    
    print("⚠️  IMPORTANTE: Después de ejecutar este script,")
    print("   actualiza el modelo Factura en app.py")
    print("   (ver instrucciones al final del script)\n")
    
    respuesta = input("¿Continuar con la migración? (si/no): ")
    
    if respuesta.lower() in ['si', 's', 'yes', 'y']:
        migrate_factura_complete()
    else:
        print("❌ Migración cancelada")