from sqlalchemy import create_engine, text

engine = create_engine('postgresql://postgres:12345@localhost:5432/tdm')
with engine.connect() as conn:
    result = conn.execute(text('SELECT version_num FROM alembic_version')).fetchall()
    print('Current migration:', result if result else 'None')
