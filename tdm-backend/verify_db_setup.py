"""Verify database setup and Alembic migrations."""
import sys
from sqlalchemy import create_engine, inspect, text
from config import settings

def check_database(name: str, url: str) -> bool:
    """Check if database is accessible and list tables."""
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            # Test connection
            conn.execute(text("SELECT 1"))
            
        inspector = inspect(engine)
        tables = sorted(inspector.get_table_names())
        
        print(f"\n✅ {name} Database Connected: {url.split('@')[1]}")
        print(f"   Tables: {len(tables)}")
        for table in tables:
            print(f"      - {table}")
        
        engine.dispose()
        return True
    except Exception as e:
        print(f"\n❌ {name} Database Error: {e}")
        return False

def check_alembic() -> bool:
    """Check Alembic migration status."""
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        from alembic.runtime.migration import MigrationContext
        from database import engine
        
        # Get migration context
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current_rev = context.get_current_revision()
        
        # Get script directory
        alembic_cfg = Config("alembic.ini")
        script = ScriptDirectory.from_config(alembic_cfg)
        head_rev = script.get_current_head()
        
        print(f"\n✅ Alembic Migrations")
        print(f"   Current: {current_rev[:12] if current_rev else 'None'}")
        print(f"   Latest:  {head_rev[:12] if head_rev else 'None'}")
        
        if not current_rev:
            print(f"   Status:  ⚠️  No migrations applied - run: python -m alembic upgrade head")
            return False
        elif current_rev == head_rev:
            print(f"   Status:  ✅ Up to date")
            return True
        else:
            print(f"   Status:  ⚠️  Out of date - run: python -m alembic upgrade head")
            return False
    except Exception as e:
        print(f"\n❌ Alembic Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all checks."""
    print("=" * 60)
    print("TDM Database Setup Verification")
    print("=" * 60)
    
    results = []
    
    # Check metadata database
    results.append(check_database("Metadata (tdm)", settings.database_url))
    
    # Check target database
    results.append(check_database("Target (tdm_target)", settings.target_database_url))
    
    # Check Alembic
    results.append(check_alembic())
    
    # Summary
    print("\n" + "=" * 60)
    if all(results):
        print("✅ All checks passed! Database setup is complete.")
        print("\nYou can now:")
        print("  1. Start backend: python -m uvicorn main:app --reload --port 8002")
        print("  2. Execute workflows that use both databases")
        print("  3. Provision data to tdm_target database")
    else:
        print("❌ Some checks failed. Please review errors above.")
        sys.exit(1)
    print("=" * 60)

if __name__ == "__main__":
    main()
