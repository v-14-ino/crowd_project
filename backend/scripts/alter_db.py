import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from database.connection import engine
from sqlalchemy import text

def alter_tables():
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE incidents ADD COLUMN human_status VARCHAR(80) NOT NULL DEFAULT 'Awaiting Review'"))
            print("Added human_status to incidents")
        except Exception as e:
            print(f"Skipping human_status (may already exist): {e}")

        try:
            conn.execute(text("ALTER TABLE responder_verifications ADD COLUMN responder_name VARCHAR(120) NULL"))
            print("Added responder_name to responder_verifications")
        except Exception as e:
            print(f"Skipping responder_name (may already exist): {e}")

if __name__ == "__main__":
    alter_tables()
    print("Database alteration complete.")
