"""
Script para agregar las tablas de domicilios a la base de datos existente
"""
from app import app, db
from sqlalchemy import inspect

def actualizar_base_datos():
    with app.app_context():
        inspector = inspect(db.engine)
        tablas_existentes = inspector.get_table_names()
        
        print("🔍 Verificando tablas existentes...")
        print(f"Tablas actuales: {len(tablas_existentes)}")
        
        # Crear todas las tablas (solo creará las que no existan)
        db.create_all()
        
        inspector = inspect(db.engine)
        tablas_actualizadas = inspector.get_table_names()
        
        print(f"\n✅ Tablas después de actualizar: {len(tablas_actualizadas)}")
        
        nuevas_tablas = set(tablas_actualizadas) - set(tablas_existentes)
        if nuevas_tablas:
            print(f"\n🆕 Nuevas tablas creadas: {nuevas_tablas}")
        else:
            print("\n✓ No se crearon tablas nuevas (ya existían)")
        
        # Crear zonas de delivery por defecto
        from app import ZonaDelivery
        if ZonaDelivery.query.count() == 0:
            zonas_default = [
                {
                    'nombre': 'Centro',
                    'barrios': 'Centro, Plaza Principal, Parque',
                    'costo_envio': 2000,
                    'tiempo_estimado': 20,
                    'orden': 1
                },
                {
                    'nombre': 'Zona Norte',
                    'barrios': 'Villa Nueva, Los Pinos, El Bosque',
                    'costo_envio': 3000,
                    'tiempo_estimado': 30,
                    'orden': 2
                },
                {
                    'nombre': 'Zona Sur',
                    'barrios': 'San Antonio, La Esperanza, Brisas',
                    'costo_envio': 3000,
                    'tiempo_estimado': 30,
                    'orden': 3
                },
                {
                    'nombre': 'Zona Este',
                    'barrios': 'El Jardín, Las Palmas, Vista Hermosa',
                    'costo_envio': 3500,
                    'tiempo_estimado': 35,
                    'orden': 4
                }
            ]
            
            for zona_data in zonas_default:
                zona = ZonaDelivery(**zona_data)
                db.session.add(zona)
            
            db.session.commit()
            print("\n✅ Zonas de delivery creadas correctamente")
        
        print("\n✅ Base de datos actualizada correctamente")
        print("\n📝 Próximo paso: Ejecuta 'python app.py' para iniciar el servidor")

if __name__ == '__main__':
    actualizar_base_datos()