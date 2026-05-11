"""
Script de migración para agregar campos faltantes en domicilios
Ejecutar con: python migracion_domicilios.py
"""

from app import app, db, ItemDomicilio
from sqlalchemy import text

def migrar_domicilios():
    with app.app_context():
        print("🔄 Iniciando migración de domicilios...")
        
        try:
            # 1. Agregar campo estado_cocina a item_domicilio
            print("📝 Agregando campo 'estado_cocina' a item_domicilio...")
            try:
                with db.engine.connect() as conn:
                    conn.execute(text(
                        "ALTER TABLE item_domicilio ADD COLUMN estado_cocina VARCHAR(20) DEFAULT 'pendiente'"
                    ))
                    conn.commit()
                print("✅ Campo 'estado_cocina' agregado exitosamente")
            except Exception as e:
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    print("⚠️  Campo 'estado_cocina' ya existe, omitiendo...")
                else:
                    raise e
            
            # 2. Actualizar items existentes que no tengan estado_cocina
            print("🔄 Actualizando items existentes...")
            items_sin_estado = ItemDomicilio.query.filter(
                (ItemDomicilio.estado_cocina == None) | (ItemDomicilio.estado_cocina == '')
            ).all()
            
            for item in items_sin_estado:
                item.estado_cocina = 'listo'  # Marcar items antiguos como listos
            
            db.session.commit()
            print(f"✅ {len(items_sin_estado)} items actualizados")
            
            # 3. Verificar la estructura
            print("\n🔍 Verificando estructura de la tabla...")
            with db.engine.connect() as conn:
                result = conn.execute(text("PRAGMA table_info(item_domicilio)"))
                columnas = [row[1] for row in result]
                print(f"Columnas en item_domicilio: {', '.join(columnas)}")
                
                if 'estado_cocina' in columnas:
                    print("✅ Migración completada exitosamente")
                else:
                    print("❌ Error: Campo estado_cocina no se agregó correctamente")
            
            print("\n✅ Migración finalizada correctamente")
            print("📌 Ahora puedes reiniciar la aplicación")
            
        except Exception as e:
            print(f"❌ Error durante la migración: {str(e)}")
            db.session.rollback()
            raise e

if __name__ == "__main__":
    migrar_domicilios()