import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api import auth_router, database_router, evidence_router, incidents_router, reports_router

app = FastAPI(
    title="Municipality Crowd Verification API",
    description="Phase 2 backend for the Municipality Crowd Verification System",
    version="0.2.0",
)

# ALLOWED_ORIGINS is used for production deployment
allowed_origins_env = os.environ.get("ALLOWED_ORIGINS")
if allowed_origins_env:
    origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
else:
    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Static file serving for evidence attachments
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
(UPLOAD_DIR / "evidence").mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(reports_router, prefix="/api/reports", tags=["reports"])
app.include_router(incidents_router, prefix="/api/incidents", tags=["incidents"])
app.include_router(evidence_router, prefix="/api", tags=["evidence"])
app.include_router(database_router, prefix="/api/database", tags=["database"])

@app.on_event("startup")
def startup_event():
    from database.base import Base
    from database.connection import engine, SessionLocal
    import models.models  # Ensure models are loaded for metadata

    # Automatically create database tables if they do not exist
    Base.metadata.create_all(bind=engine)

    from models.models import User
    from api.auth import get_password_hash
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@municipal.gov").first()
        if not admin:
            new_admin = User(
                name="System Administrator",
                email="admin@municipal.gov",
                password_hash=get_password_hash("admin123"),
                role="officer"
            )
            db.add(new_admin)
            
        officer = db.query(User).filter(User.email == "officer@municipal.gov").first()
        if not officer:
            new_officer = User(
                name="Test Officer",
                email="officer@municipal.gov",
                password_hash=get_password_hash("Officer@123"),
                role="officer"
            )
            db.add(new_officer)
            
        db.commit()
    finally:
        db.close()

@app.get("/")
def root():
    return {
        "message": "Municipality Crowd Verification API",
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}

