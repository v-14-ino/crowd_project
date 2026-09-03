import logging
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()
logger = logging.getLogger(__name__)


class DatabaseSettings(BaseSettings):
    database_host: str = Field("localhost", env="DATABASE_HOST")
    database_port: int = Field(5432, env="DATABASE_PORT")
    database_name: str = Field("municipality_verification", env="DATABASE_NAME")
    database_user: str = Field("postgres", env="DATABASE_USER")
    database_password: Optional[str] = Field(None, env="DATABASE_PASSWORD")
    database_url: Optional[str] = Field(None, env="DATABASE_URL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        if not self.database_password:
            raise ValueError(
                "DATABASE_PASSWORD is required when DATABASE_URL is not provided."
            )
        return (
            f"postgresql+psycopg2://{self.database_user}:"
            f"{self.database_password}@{self.database_host}:"
            f"{self.database_port}/{self.database_name}"
        )


settings = DatabaseSettings()

engine = create_engine(settings.sqlalchemy_database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
