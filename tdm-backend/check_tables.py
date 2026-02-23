from database import engine
from sqlalchemy import inspect, text

inspector = inspect(engine)
all_tables = inspector.get_table_names()
print(f"Total tables: {len(all_tables)}")
print(f"Has alembic_version: {'alembic_version' in all_tables}")

if 'alembic_version' in all_tables:
    with engine.connect() as conn:
        result = list(conn.execute(text('SELECT version_num FROM alembic_version')))
        print(f"Alembic version: {result}")
else:
    print("alembic_version table not found - need to run migration")
