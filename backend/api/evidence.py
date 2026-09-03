import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database.connection import get_db
from models.models import (
    ExternalEvidence,
    Incident,
    IncidentReport,
    Report,
    ResponderVerification,
)
from schemas.evidence import EvidenceAttachResponse, EvidenceCreateRequest, EvidenceResponse
from schemas.incident import ExternalEvidenceItem
from services.verification_engine import VerificationEngine

router = APIRouter()

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads" / "evidence"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/pjpeg",
    "image/png",
    "image/x-png",
    "image/webp",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def determine_freshness(observed_time: Optional[datetime]) -> str:
    if not observed_time:
        return "Fresh"
    now = datetime.now(timezone.utc) if observed_time.tzinfo else datetime.utcnow()
    diff_hours = (now - observed_time).total_seconds() / 3600.0
    if diff_hours <= 24:
        return "Fresh"
    elif diff_hours <= 72:
        return "Aging"
    else:
        return "Stale"


def validate_and_save_upload(upload_file: UploadFile) -> tuple[str, str, str, int, str]:
    """
    Validates file extension, MIME type, and size.
    Saves file to safe server-side generated path to prevent directory traversal.
    Returns (original_filename, safe_filepath, relative_url, file_size, mime_type).
    """
    original_name = upload_file.filename or "evidence.jpg"
    ext = Path(original_name).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    mime_type = upload_file.content_type or "application/octet-stream"
    if mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported MIME type '{mime_type}'. Must be an image (JPEG, PNG, WEBP).",
        )

    # Read and validate size
    content = upload_file.file.read()
    file_size = len(content)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of 10MB ({file_size} bytes provided).",
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes).",
        )

    # Generate safe random filename to prevent path traversal
    safe_filename = f"evd_{uuid.uuid4().hex[:12]}_{int(datetime.utcnow().timestamp())}{ext}"
    destination_path = UPLOAD_DIR / safe_filename

    # Ensure path stays strictly inside UPLOAD_DIR
    resolved_path = destination_path.resolve()
    if not str(resolved_path).startswith(str(UPLOAD_DIR.resolve())):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file destination path detected.",
        )

    with open(destination_path, "wb") as f:
        f.write(content)

    relative_url = f"/uploads/evidence/{safe_filename}"
    return original_name, str(destination_path), relative_url, file_size, mime_type


def recalculate_incident(incident: Incident, db: Session) -> dict:
    """
    Triggers VerificationEngine update for the incident to ensure confidence and priority scores reflect evidence changes.
    """
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
    return engine.update_evaluation_labels()


@router.post("/incidents/{incident_id}/evidence", status_code=status.HTTP_201_CREATED, response_model=EvidenceAttachResponse)
async def attach_evidence(
    incident_id: str,
    request: Request,
    file: Optional[UploadFile] = File(None),
    source_type: Optional[str] = Form(None),
    source_status: Optional[str] = Form(None),
    observed_at: Optional[str] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    details: Optional[str] = Form(None),
    report_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Attaches evidence (uploaded photo or simulated metadata) to a municipal incident,
    recalculates VerificationEngine canonical evaluation, and returns complete before/after deltas.
    """
    try:
        incident = db.execute(select(Incident).where(Incident.incident_id == incident_id)).scalar_one_or_none()
        if not incident:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Incident '{incident_id}' not found.")

        # Capture pre-attachment evaluation metrics
        prev_confidence = incident.confidence_score
        prev_priority = incident.priority_score
        prev_status = incident.status

        # Check if request was sent as application/json
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            body_data = await request.json()
            source_type = body_data.get("source_type", "Citizen")
            source_status = body_data.get("source_status", "Standard")
            obs_str = body_data.get("observed_at")
            parsed_observed_at = datetime.fromisoformat(obs_str.replace("Z", "+00:00")) if obs_str else datetime.utcnow()
            latitude = body_data.get("latitude")
            longitude = body_data.get("longitude")
            details = body_data.get("details", "")
            report_id = body_data.get("report_id")
            filename = None
            file_path = None
            file_url = None
            file_size = None
            mime_type = None
        else:
            # Multipart form data with optional file upload
            parsed_observed_at = None
            if observed_at:
                try:
                    parsed_observed_at = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
                except ValueError:
                    parsed_observed_at = datetime.utcnow()
            else:
                parsed_observed_at = datetime.utcnow()

            source_type = source_type or "Citizen"
            source_status = source_status or "Standard"
            details = details or ""

            filename = None
            file_path = None
            file_url = None
            file_size = None
            mime_type = None

            if file is not None and file.filename:
                filename, file_path, file_url, file_size, mime_type = validate_and_save_upload(file)

        # Resolve report database id if report_id string was provided
        db_report_id = None
        if report_id:
            rep = db.execute(select(Report).where(Report.report_id == str(report_id))).scalar_one_or_none()
            if rep:
                db_report_id = rep.id

        # Duplicate evidence check
        existing_dup = db.execute(
            select(ExternalEvidence).where(
                ExternalEvidence.incident_id == incident.id,
                ExternalEvidence.source_type == source_type,
                ExternalEvidence.details == details,
            )
        ).scalars().first()

        if existing_dup and (
            (filename and existing_dup.filename == filename)
            or (not filename and not existing_dup.filename)
        ):
            eval_dict = recalculate_incident(incident, db)
            return EvidenceAttachResponse(
                id=existing_dup.id,
                evidence_id=existing_dup.evidence_id,
                incident_id=existing_dup.incident_id,
                report_id=existing_dup.report_id,
                source_type=existing_dup.source_type,
                source_status=existing_dup.source_status,
                observed_at=existing_dup.observed_at,
                freshness_status=existing_dup.freshness_status,
                details=existing_dup.details,
                filename=existing_dup.filename,
                file_url=existing_dup.file_url,
                file_size=existing_dup.file_size,
                mime_type=existing_dup.mime_type,
                latitude=existing_dup.latitude,
                longitude=existing_dup.longitude,
                created_at=existing_dup.created_at,
                previous_confidence_score=prev_confidence,
                updated_confidence_score=incident.confidence_score,
                previous_priority_score=prev_priority,
                updated_priority_score=incident.priority_score,
                previous_status=prev_status,
                status=incident.status,
                freshness=incident.freshness_status,
                confidence_explanations=eval_dict.get("confidence_explanations", []),
                priority_explanations=eval_dict.get("priority_explanations", []),
                recommended_action=eval_dict.get("recommended_action", ""),
            )

        freshness_status = determine_freshness(parsed_observed_at)
        evidence_code = f"EVD-{uuid.uuid4().hex[:8].upper()}"

        evidence_record = ExternalEvidence(
            evidence_id=evidence_code,
            incident_id=incident.id,
            report_id=db_report_id,
            source_type=source_type,
            source_status=source_status,
            observed_at=parsed_observed_at,
            freshness_status=freshness_status,
            details=details,
            filename=filename,
            file_path=file_path,
            file_url=file_url,
            file_size=file_size,
            mime_type=mime_type,
            latitude=latitude,
            longitude=longitude,
        )
        db.add(evidence_record)
        db.flush()

        # Recalculate incident evaluation so scores reflect new evidence
        eval_dict = recalculate_incident(incident, db)
        db.commit()
        db.refresh(evidence_record)

        return EvidenceAttachResponse(
            id=evidence_record.id,
            evidence_id=evidence_record.evidence_id,
            incident_id=evidence_record.incident_id,
            report_id=evidence_record.report_id,
            source_type=evidence_record.source_type,
            source_status=evidence_record.source_status,
            observed_at=evidence_record.observed_at,
            freshness_status=evidence_record.freshness_status,
            details=evidence_record.details,
            filename=evidence_record.filename,
            file_url=evidence_record.file_url,
            file_size=evidence_record.file_size,
            mime_type=evidence_record.mime_type,
            latitude=evidence_record.latitude,
            longitude=evidence_record.longitude,
            created_at=evidence_record.created_at,
            previous_confidence_score=prev_confidence,
            updated_confidence_score=incident.confidence_score,
            previous_priority_score=prev_priority,
            updated_priority_score=incident.priority_score,
            previous_status=prev_status,
            status=incident.status,
            freshness=incident.freshness_status,
            confidence_explanations=eval_dict.get("confidence_explanations", []),
            priority_explanations=eval_dict.get("priority_explanations", []),
            recommended_action=eval_dict.get("recommended_action", ""),
        )
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database error occurred.") from exc


@router.get("/incidents/{incident_id}/evidence", response_model=List[ExternalEvidenceItem])
def get_incident_evidence(incident_id: str, db: Session = Depends(get_db)):
    """
    Retrieves all attached evidence for an incident.
    """
    try:
        incident = db.execute(select(Incident).where(Incident.incident_id == incident_id)).scalar_one_or_none()
        if not incident:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Incident '{incident_id}' not found.")

        evidence_list = db.execute(
            select(ExternalEvidence).where(ExternalEvidence.incident_id == incident.id).order_by(ExternalEvidence.created_at.desc())
        ).scalars().all()

        return evidence_list
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database error occurred.") from exc


@router.delete("/evidence/{evidence_id}", status_code=status.HTTP_200_OK)
def delete_evidence(evidence_id: str, db: Session = Depends(get_db)):
    """
    Deletes an evidence record and removes its physical file from disk.
    """
    try:
        # Check by string evidence_id or integer id
        evidence = None
        if evidence_id.isdigit():
            evidence = db.execute(select(ExternalEvidence).where(ExternalEvidence.id == int(evidence_id))).scalar_one_or_none()
        if not evidence:
            evidence = db.execute(select(ExternalEvidence).where(ExternalEvidence.evidence_id == evidence_id)).scalar_one_or_none()

        if not evidence:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence '{evidence_id}' not found.")

        incident = db.execute(select(Incident).where(Incident.id == evidence.incident_id)).scalar_one_or_none()

        # Remove physical file if present
        if evidence.file_path and os.path.exists(evidence.file_path):
            try:
                os.remove(evidence.file_path)
            except OSError:
                pass

        db.delete(evidence)
        db.flush()

        if incident:
            recalculate_incident(incident, db)

        db.commit()
        return {"message": "Evidence deleted successfully", "evidence_id": evidence_id}
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database error occurred.") from exc
