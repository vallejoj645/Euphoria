"""
Script para actualizar la base de datos agregando el campo precio_unitario
"""

from app import app, db
import sqlite3

def update_database():
    with app.app_context():
        # Conectar a la base de datos
        conn = sqlite3.connect('restaurante.db')
        cursor = conn.cursor()
        
        try:
            # Verificar si la columna ya existe
            cursor.execute("PRAGMA table_info(pedido)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'precio_unitario' not in columns:
                print("Agregando columna precio_unitario...")
                cursor.execute("ALTER TABLE pedido ADD COLUMN precio_unitario FLOAT DEFAULT 0")
                conn.commit()
                print("✓ Columna agregada exitosamente")
            else:
                print("✓ La columna precio_unitario ya existe")

            # Agregar columna estado_actualizado para notificaciones (si no existe)
            if 'estado_actualizado' not in columns:
                print("Agregando columna estado_actualizado...")
                cursor.execute("ALTER TABLE pedido ADD COLUMN estado_actualizado DATETIME")
                # Inicializar valores para pedidos existentes (usar fecha de creación como proxy)
                cursor.execute("UPDATE pedido SET estado_actualizado = fecha WHERE estado = 'listo' AND estado_actualizado IS NULL")
                conn.commit()
                print("✓ Columna 'estado_actualizado' agregada exitosamente")
            else:
                print("✓ La columna 'estado_actualizado' ya existe")

            # Crear tabla consumo_interno si no existe (para registrar consumos internos)
            print("Verificando tabla 'consumo_interno'...")
            cursor.execute("CREATE TABLE IF NOT EXISTS consumo_interno (\n                id INTEGER PRIMARY KEY,\n                item_id INTEGER NOT NULL,\n                cantidad INTEGER DEFAULT 1,\n                costo FLOAT DEFAULT 0,\n                fecha DATETIME DEFAULT CURRENT_TIMESTAMP,\n                usuario_id INTEGER NOT NULL,\n                notas TEXT\n            )")
            conn.commit()
            print("✓ Tabla 'consumo_interno' verificada/creada")
            
            conn.close()
            print("\n¡Base de datos actualizada correctamente!")
            
        except Exception as e:
            print(f"Error al actualizar la base de datos: {e}")
            conn.rollback()
            conn.close()

if __name__ == "__main__":
    update_database()