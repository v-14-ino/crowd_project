import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from database.base import Base
from database.connection import engine

# Import model classes so they register with SQLAlchemy metadata.
import models.models  # noqa: F401


def create_database_schema() -> None:
    """Create database tables for the application."""
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    create_database_schema()
    print("Database schema initialized.")
