from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from database.connection import get_db
from models.models import (
    EvaluationLabel,
    ExternalEvidence,
    Incident,
    IncidentReport,
    Report,
    ResponderVerification,
)
from schemas.incident import (
    ExternalEvidenceItem,
    IncidentOfficerDetail,
    IncidentOfficerSummary,
    IncidentStats,
    ReportItem,
    ResponderVerificationCreate,
    ResponderVerificationItem,
)
from schemas.report import ReportSummary
from services.verification_engine import VerificationEngine
from api.auth import get_current_user
from models.models import User

router = APIRouter()


@router.get("/stats", response_model=IncidentStats)
def get_incident_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Returns aggregate KPI stats derived directly from canonical incident evaluation fields.
    """
    try:
        total = db.execute(select(func.count(Incident.id))).scalar_one()
        critical = db.execute(select(func.count(Incident.id)).where(Incident.priority_level == "Critical")).scalar_one()
        high = db.execute(select(func.count(Incident.id)).where(Incident.priority_level == "High")).scalar_one()
        corroborated = db.execute(select(func.count(Incident.id)).where(Incident.status == "Corroborated")).scalar_one()
        verified = db.execute(select(func.count(Incident.id)).where(Incident.status == "Verified")).scalar_one()
        pending = db.execute(select(func.count(Incident.id)).where(Incident.status == "Pending")).scalar_one()
        conflicted = db.execute(select(func.count(Incident.id)).where(Incident.status == "Conflicted")).scalar_one()
        stale = db.execute(select(func.count(Incident.id)).where(Incident.freshness_status == "Stale")).scalar_one()

        return IncidentStats(
            total_incidents=total,
            critical_incidents=critical,
            high_priority_incidents=high,
            corroborated_incidents=corroborated,
            verified_incidents=verified,
            pending_incidents=pending,
            conflicted_incidents=conflicted,
            stale_incidents=stale,
        )
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database is unavailable") from exc


@router.get("", response_model=List[IncidentOfficerSummary])
def list_incidents(
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority_level: Optional[str] = Query(None),
    confidence_level: Optional[str] = Query(None),
    freshness: Optional[str] = Query(None),
    zone: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns prioritized incident queue for municipal officers with full SQL filtering and sorting.
    """
    try:
        query = select(Incident)

        search_term = search.strip() if search and search.strip() else None
        if search_term:
            query = query.where(
                (Incident.incident_id.ilike(f"%{search_term}%"))
                | (Incident.category.ilike(f"%{search_term}%"))
                | (Incident.issue_type.ilike(f"%{search_term}%"))
                | (Incident.zone.ilike(f"%{search_term}%"))
                | (
                    Incident.id.in_(
                        select(IncidentReport.incident_id)
                        .join(Report, IncidentReport.report_id == Report.id)
                        .where(Report.report_id.ilike(f"%{search_term}%"))
                    )
                )
            )


        if category and category != "All":
            query = query.where(Incident.category == category)

        if zone and zone != "All":
            query = query.where(Incident.zone == zone)

        if status and status != "All":
            query = query.where(Incident.status == status)

        if priority_level and priority_level != "All":
            query = query.where(Incident.priority_level == priority_level)

        if confidence_level and confidence_level != "All":
            query = query.where(Incident.confidence_level == confidence_level)

        if freshness and freshness != "All":
            query = query.where(Incident.freshness_status == freshness)

        # Primary sort by priority_score descending, secondary by created_at descending
        query = query.order_by(Incident.priority_score.desc(), Incident.created_at.desc())
        query = query.limit(page_size).offset((page - 1) * page_size)

        incidents = db.execute(query).scalars().all()

        summaries = [
            IncidentOfficerSummary(
                incident_id=inc.incident_id,
                category=inc.category,
                issue_type=inc.issue_type,
                zone=inc.zone,
                status=inc.status,
                human_status=inc.human_status,
                priority_score=inc.priority_score,
                priority_level=inc.priority_level,
                confidence_score=inc.confidence_score,
                confidence_level=inc.confidence_level,
                freshness=inc.freshness_status,
                total_reports_count=inc.total_reports_count,
                independent_reports_count=inc.independent_reports_count,
                duplicate_reports_count=inc.duplicate_reports_count,
                latitude=inc.latitude,
                longitude=inc.longitude,
                last_reported_time=inc.last_reported_time,
                created_at=inc.created_at,
                updated_at=inc.updated_at,
            )
            for inc in incidents
        ]

        return summaries
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database is unavailable") from exc



@router.get("/{incident_id}", response_model=IncidentOfficerDetail)
def get_incident(incident_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Returns complete incident drill-down detail with explainability and related records.
    """
    try:
        incident = db.execute(select(Incident).where(Incident.incident_id == incident_id)).scalar_one_or_none()
        if incident is None:
            raise HTTPException(status_code=404, detail="Incident not found")

        reports = db.execute(
            select(Report)
            .join(IncidentReport, Report.id == IncidentReport.report_id)
            .where(IncidentReport.incident_id == incident.id)
        ).scalars().all()

        evidence = db.execute(
            select(ExternalEvidence).where(ExternalEvidence.incident_id == incident.id)
        ).scalars().all()

        verifications = db.execute(
            select(ResponderVerification).where(ResponderVerification.incident_id == incident.id)
        ).scalars().all()

        engine = VerificationEngine(
            db=db,
            incident=incident,
            reports=reports,
            evidence=evidence,
            verifications=verifications,
        )
        summary_dict = engine.evaluate_full_summary()

        report_items = [ReportItem.model_validate(r) for r in reports]
        evidence_items = [ExternalEvidenceItem.model_validate(e) for e in evidence]
        verification_items = [ResponderVerificationItem.model_validate(v) for v in verifications]

        return IncidentOfficerDetail(
            **summary_dict,
            reports=report_items,
            evidence=evidence_items,
            responder_verifications=verification_items,
        )
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database is unavailable") from exc


@router.get("/{incident_id}/reports", response_model=List[ReportSummary])
def get_incident_reports(incident_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        incident = db.execute(select(Incident).where(Incident.incident_id == incident_id)).scalar_one_or_none()
        if incident is None:
            raise HTTPException(status_code=404, detail="Incident not found")

        query = (
            select(Report)
            .join(IncidentReport, Report.id == IncidentReport.report_id)
            .where(IncidentReport.incident_id == incident.id)
        )
        reports = db.execute(query).scalars().all()
        return reports
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database is unavailable") from exc

@router.post("/{incident_id}/verification", response_model=ResponderVerificationItem)
def create_responder_verification(
    incident_id: str,
    payload: ResponderVerificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submits a human responder decision (VERIFY, REJECT, NEEDS MORE EVIDENCE).
    """
    try:
        incident = db.execute(select(Incident).where(Incident.incident_id == incident_id)).scalar_one_or_none()
        if incident is None:
            raise HTTPException(status_code=404, detail="Incident not found")

        decision_map = {
            "VERIFY": "Verified",
            "REJECT": "Rejected",
            "ESCALATE": "Needs More Evidence",
            "NEEDS MORE EVIDENCE": "Needs More Evidence"
        }

        decision_key = payload.decision.upper().strip()
        if decision_key not in decision_map:
            raise HTTPException(status_code=400, detail="Invalid decision value.")

        mapped_decision = decision_map[decision_key]

        verification = ResponderVerification(
            incident_id=incident.id,
            responder_name=payload.responder_name,
            verification_status=mapped_decision,
            notes=payload.rationale,
            verified_at=func.now()
        )
        db.add(verification)
        db.flush()

        # Update the Incident's human decision tracking
        incident.human_status = mapped_decision

        # Trigger VerificationEngine recalculation
        reports = db.execute(
            select(Report)
            .join(IncidentReport, Report.id == IncidentReport.report_id)
            .where(IncidentReport.incident_id == incident.id)
        ).scalars().all()

        evidence = db.execute(
            select(ExternalEvidence).where(ExternalEvidence.incident_id == incident.id)
        ).scalars().all()

        verifications = db.execute(
            select(ResponderVerification).where(ResponderVerification.incident_id == incident.id)
        ).scalars().all()

        engine = VerificationEngine(
            db=db,
            incident=incident,
            reports=reports,
            evidence=evidence,
            verifications=verifications,
        )
        engine.update_evaluation_labels()

        db.commit()
        db.refresh(verification)

        return ResponderVerificationItem.model_validate(verification)

    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Database is unavailable") from exc

