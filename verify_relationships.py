"""
Script para verificar y corregir las relaciones de la base de datos
Ejecutar: python verify_relationships.py
"""

from app import app, db, Factura, Domicilio

def verify_relationships():
    """Verifica que las relaciones entre Factura y Domicilio funcionen"""
    
    with app.app_context():
        print("\n" + "="*60)
        print("  VERIFICACIÓN DE RELACIONES")
        print("="*60 + "\n")
        
        # Verificar facturas
        facturas = Factura.query.all()
        print(f"📊 Total de facturas: {len(facturas)}")
        
        for factura in facturas:
            print(f"\n📄 Factura: {factura.numero_consecutivo}")
            print(f"   - sesion_id: {factura.sesion_id}")
            
            # Verificar si tiene sesión
            if factura.sesion_id:
                print(f"   - Tipo: MESA")
                if factura.sesion:
                    print(f"   - Mesa: {factura.sesion.mesa.numero}")
                else:
                    print(f"   ⚠️  ERROR: sesion_id existe pero no se puede acceder")
            else:
                print(f"   - Tipo: DOMICILIO")
                
                # Buscar domicilio asociado
                domicilio = Domicilio.query.filter_by(factura_id=factura.id).first()
                if domicilio:
                    print(f"   - Domicilio ID: {domicilio.id}")
                    print(f"   - Cliente: {domicilio.cliente_nombre}")
                    
                    # Verificar relación bidireccional
                    try:
                        test = factura.domicilios.first()
                        print(f"   ✅ Relación bidireccional OK")
                    except Exception as e:
                        print(f"   ⚠️  ERROR en relación: {str(e)}")
                else:
                    print(f"   ⚠️  ADVERTENCIA: No se encontró domicilio asociado")
        
        print("\n" + "="*60)
        print("✅ Verificación completada")
        print("="*60 + "\n")


if __name__ == "__main__":
    verify_relationships()