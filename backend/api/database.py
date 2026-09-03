from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database.connection import get_db
from models.models import ExternalEvidence, Incident, ResponderVerification, Report
from schemas.database import DatabaseStats

router = APIRouter()


@router.get("/stats", response_model=DatabaseStats)
def database_stats(db: Session = Depends(get_db)):
    try:
        reports_count = db.execute(select(func.count(Report.id))).scalar_one()
        incidents_count = db.execute(select(func.count(Incident.id))).scalar_one()
        external_count = db.execute(select(func.count(ExternalEvidence.id))).scalar_one()
        responder_count = db.execute(select(func.count(ResponderVerification.id))).scalar_one()
        return DatabaseStats(
            reports=reports_count,
            incidents=incidents_count,
            external_evidence=external_count,
            responder_verifications=responder_count,
        )
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database is unavailable")
