# Restaurante — Despliegue en Railway

Instrucciones rápidas para desplegar en Railway ✅

1. Preparar variables de entorno
   - `SECRET_KEY` (obligatorio)
   - `DATABASE_URL` (Postgres). Railway suele proporcionar esta variable al crear un servicio de Postgres.
   - `PORT` (Railway la provee automáticamente al ejecutar la app)

2. Dependencias
   - El proyecto ya incluye `gunicorn` y `psycopg2-binary` en `requirements.txt`.
   - En local, puede usar `.env` (copiar `.env.example`) y ejecutar `pip install -r requirements.txt`.

3. Inicializar la base de datos
   - Local: `python create_db.py`
   - En producción en Railway: usar un 'Release Command' que ejecute `python create_db.py` o correrlo manualmente desde un shell en Railway.

4. Procfile
   - `web: gunicorn --timeout 120 --workers 3 --threads 2 --worker-class gthread --bind 0.0.0.0:$PORT --log-file - app:app`

5. Notas importantes
   - La aplicación prioriza `DATABASE_URL`. Si la URL contiene `postgres://`, el código la convierte a `postgresql://` para compatibilidad con SQLAlchemy.
   - He añadido `runtime.txt` (Python 3.13.5) y un `.env.example`.
   - Para pruebas locales, asegúrate de crear la BD con `python create_db.py` después de instalar dependencias.

6. Release / migraciones automáticas (opcional)
   - En Railway puedes configurar un "Release Command" que ejecute `python create_db.py` para crear o migrar la base de datos automáticamente al desplegar.

7. Troubleshooting (Windows)
   - En Windows la instalación de `psycopg2-binary` puede fallar si no están instaladas las dependencias de Postgres (pg_config). Soluciones:
     - Usar WSL o un contenedor Linux para el desarrollo local.
     - Instalar PostgreSQL localmente y asegurarte de que `pg_config` esté en el PATH.
     - En producción en Railway no suele ser un problema porque se usan wheels compatibles.

8. Consumo Interno (administración)
   - He añadido una sección para registrar "Consumo Interno" (solo para administradores): `Consumo Interno` permite registrar qué ítems del menú se retiran para uso interno y cuánto le cuesta al dueño (costo por unidad). Esta acción **no** afecta gastos ni ingresos automáticamente, es solo un registro para control interno.
   - Rutas:
     - `GET /consumo_interno` — lista de consumos (solo admin)
     - `GET/POST /consumo_interno/nuevo` — registrar nuevo consumo (solo admin)
     - `POST /consumo_interno/<id>/eliminar` — eliminar registro (solo admin)
   - Para crear la tabla en la BD local puedes ejecutar: `python update_database.py` (o `python create_db.py` en caso de base vacía).

¡Listo! Si quieres, añado export CSV o filtros por periodo para los consumos.
