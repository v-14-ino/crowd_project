import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
DATABASE_PORT = os.getenv("DATABASE_PORT", "5432")
DATABASE_USER = os.getenv("DATABASE_USER", "postgres")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE_NAME = os.getenv("DATABASE_NAME", "municipality_verification")

if not DATABASE_PASSWORD:
    raise SystemExit("DATABASE_PASSWORD must be set in backend/.env to create the database.")

connection = psycopg2.connect(
    host=DATABASE_HOST,
    port=DATABASE_PORT,
    dbname="postgres",
    user=DATABASE_USER,
    password=DATABASE_PASSWORD,
)
connection.autocommit = True
with connection.cursor() as cursor:
    cursor.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s",
        (DATABASE_NAME,),
    )
    exists = cursor.fetchone() is not None
    if exists:
        print(f"Database '{DATABASE_NAME}' already exists.")
    else:
        cursor.execute(sql.SQL("CREATE DATABASE {};" ).format(sql.Identifier(DATABASE_NAME)))
        print(f"Created database '{DATABASE_NAME}'.")
connection.close()
