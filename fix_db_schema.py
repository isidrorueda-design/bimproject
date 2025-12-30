from app.database import engine
from sqlalchemy import text

def fix_schema():
    with engine.connect() as connection:
        print("Updating contracts table...")
        try:
            connection.execute(text("ALTER TABLE contracts ADD COLUMN start_date DATE"))
            print("- Added start_date")
        except Exception as e:
            print(f"- start_date info: {e}")

        try:
            connection.execute(text("ALTER TABLE contracts ADD COLUMN end_date DATE"))
            print("- Added end_date")
        except Exception as e:
            print(f"- end_date info: {e}")
            
        try:
            connection.execute(text("ALTER TABLE contracts ADD COLUMN avance_fisico FLOAT DEFAULT 0.0"))
            print("- Added avance_fisico")
        except Exception as e:
            print(f"- avance_fisico info: {e}")

        print("Updating contract_items table...")
        try:
            connection.execute(text("ALTER TABLE contract_items ADD COLUMN task_id INTEGER"))
            print("- Added task_id")
        except Exception as e:
            print(f"- task_id info: {e}")

        connection.commit()
        print("Schema update finished.")

if __name__ == "__main__":
    fix_schema()
