from app.database import engine
from sqlalchemy import text

def check_columns():
    try:
        with engine.connect() as connection:
            print("Checking contracts table...")
            try:
                connection.execute(text("SELECT start_date, end_date, avance_fisico FROM contracts LIMIT 1"))
                print("✅ Contracts columns exist.")
            except Exception as e:
                print(f"❌ Contracts columns MISSING: {e}")

            print("Checking contract_items table...")
            try:
                connection.execute(text("SELECT task_id FROM contract_items LIMIT 1"))
                print("✅ ContractItems columns exist.")
            except Exception as e:
                print(f"❌ ContractItems columns MISSING: {e}")

    except Exception as e:
        print(f"Critical DB connection error: {e}")

if __name__ == "__main__":
    check_columns()
