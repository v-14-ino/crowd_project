from datetime import datetime
import logging
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database.connection import get_db
from models.models import Incident, IncidentReport, Report
from schemas.report import (
    RecentReportItem,
    ReportCreate,
    ReportCreateResponse,
    ReportDetail,
    ReportListMetadata,
    ReportSummary,
)
from services.correlation_service import find_matching_incident

logger = logging.getLogger(__name__)

router = APIRouter()

PAGE_SIZE_MAX = 100


@router.get("/recent", response_model=List[RecentReportItem])
def get_recent_reports(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    Returns the latest citizen reports ordered by created_at DESC with their associated incident relationships.
    """
    try:
        query = select(Report).order_by(Report.created_at.desc(), Report.id.desc()).limit(limit)
        reports = db.execute(query).scalars().all()

        recent_items = []
        for rep in reports:
            # Query associated incident
            inc = db.execute(
                select(Incident)
                .join(IncidentReport, Incident.id == IncidentReport.incident_id)
                .where(IncidentReport.report_id == rep.id)
            ).scalar_one_or_none()

            incident_id = None
            relationship_type = "Awaiting Incident Assignment"
            priority_score = None
            priority_level = None
            confidence_score = None
            confidence_level = None
            verification_status = None
            total_incident_reports = 0

            if inc:
                incident_id = inc.incident_id

                # Count total reports for this incident
                total_reports = db.execute(
                    select(func.count(IncidentReport.id)).where(IncidentReport.incident_id == inc.id)
                ).scalar_one()
                total_incident_reports = total_reports

                # Check if this report was the earliest report of the incident
                first_report_id = db.execute(
                    select(IncidentReport.report_id)
                    .where(IncidentReport.incident_id == inc.id)
                    .order_by(IncidentReport.id.asc())
                    .limit(1)
                ).scalar_one_or_none()

                if first_report_id == rep.id or total_reports == 1:
                    relationship_type = f"New Incident Created: {inc.incident_id}"
                else:
                    relationship_type = f"Attached to Incident {inc.incident_id}"

                priority_score = inc.priority_score
                priority_level = inc.priority_level
                confidence_score = inc.confidence_score
                confidence_level = inc.confidence_level
                verification_status = inc.status

            recent_items.append(
                RecentReportItem(
                    report_id=rep.report_id,
                    category=rep.category,
                    issue_type=rep.issue_type,
                    description=rep.description,
                    zone=rep.zone,
                    latitude=rep.latitude,
                    longitude=rep.longitude,
                    citizen_severity=rep.citizen_severity,
                    reported_time=rep.reported_time,
                    created_at=rep.created_at,
                    location_status=rep.location_status,
                    freshness_status=rep.freshness_status,
                    incident_id=incident_id,
                    relationship_type=relationship_type,
                    total_incident_reports=total_incident_reports,
                    priority_score=priority_score,
                    priority_level=priority_level,
                    confidence_score=confidence_score,
                    confidence_level=confidence_level,
                    verification_status=verification_status,
                )
            )

        return recent_items
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database is unavailable") from exc


@router.get("", response_model=ReportListMetadata)
def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=PAGE_SIZE_MAX),
    db: Session = Depends(get_db),
):
    try:
        total = db.execute(select(func.count(Report.id))).scalar_one()
        offset = (page - 1) * page_size
        query = select(Report).offset(offset).limit(page_size)
        reports = db.execute(query).scalars().all()
        total_pages = (total + page_size - 1) // page_size
        return ReportListMetadata(
            items=reports,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database is unavailable")



@router.get("/{report_id}", response_model=ReportDetail)
def get_report(report_id: str, db: Session = Depends(get_db)):
    try:
        query = select(Report).where(Report.report_id.ilike(report_id.strip()))
        report = db.execute(query).scalar_one_or_none()
        if report is None:
            raise HTTPException(status_code=404, detail="Report not found")


        incident_query = (
            select(Incident)
            .join(IncidentReport, Incident.id == IncidentReport.incident_id)
            .where(IncidentReport.report_id == report.id)
        )
        incident = db.execute(incident_query).scalar_one_or_none()
        
        report_dict = {
            "report_id": report.report_id,
            "category": report.category,
            "issue_type": report.issue_type,
            "description": report.description,
            "zone": report.zone,
            "latitude": report.latitude,
            "longitude": report.longitude,
            "reported_time": report.reported_time,
            "citizen_severity": report.citizen_severity,
            "corroborating_reports": report.corroborating_reports,
            "location_status": report.location_status,
            "freshness_status": report.freshness_status,
            "conflicting_evidence": report.conflicting_evidence,
            "created_at": report.created_at,
            "incident_id": None
        }

        if incident:
            report_dict["incident_id"] = incident.incident_id
            report_dict["priority_score"] = incident.priority_score
            report_dict["priority_level"] = incident.priority_level
            report_dict["confidence_score"] = incident.confidence_score
            report_dict["confidence_level"] = incident.confidence_level
            report_dict["verification_status"] = incident.status
            report_dict["human_status"] = incident.human_status
            report_dict["incident_updated_at"] = incident.updated_at
            
        return ReportDetail(**report_dict)
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database is unavailable")


@router.post("", response_model=ReportCreateResponse, status_code=201)
def create_report(report_create: ReportCreate, db: Session = Depends(get_db)):
    try:
        category = report_create.category
        issue_type = report_create.issue_type
        description = report_create.description
        zone = report_create.zone
        latitude = report_create.latitude
        longitude = report_create.longitude
        citizen_severity = report_create.citizen_severity

        location_status = "Available" if latitude is not None and longitude is not None else "Missing"

        with db.begin():
            new_report = Report(
                report_id=f"RPT-{uuid4().hex[:12].upper()}",
                category=category,
                issue_type=issue_type,
                description=description,
                zone=zone,
                latitude=latitude,
                longitude=longitude,
                reported_time=datetime.utcnow(),
                citizen_severity=citizen_severity,
                location_status=location_status,
                freshness_status="Pending",
            )
            db.add(new_report)
            db.flush()

            matching_incident = find_matching_incident(db, new_report)
            if matching_incident is not None:
                incident_to_use = matching_incident
            else:
                incident_to_use = Incident(
                    incident_id=f"INC-{uuid4().hex[:12].upper()}",
                    category=category,
                    issue_type=issue_type,
                    zone=zone,
                    latitude=latitude,
                    longitude=longitude,
                    status="Pending",
                )
                db.add(incident_to_use)
                db.flush()

            incident_link = IncidentReport(
                incident_id=incident_to_use.id,
                report_id=new_report.id,
            )
            db.add(incident_link)
            db.flush()

            all_reports_for_incident = db.execute(
                select(Report)
                .join(IncidentReport, Report.id == IncidentReport.report_id)
                .where(IncidentReport.incident_id == incident_to_use.id)
            ).scalars().all()
            
            from services.verification_engine import VerificationEngine
            engine = VerificationEngine(db, incident_to_use, all_reports_for_incident)
            evaluation = engine.update_evaluation_labels()

            report_data = db.execute(select(Report).where(Report.id == new_report.id)).scalar_one()
            incident_query = (
                select(Incident.incident_id)
                .join(IncidentReport, Incident.id == IncidentReport.incident_id)
                .where(IncidentReport.report_id == new_report.id)
            )
            incident_id = db.execute(incident_query).scalar_one_or_none()
            report_data.incident_id = incident_id

        return ReportCreateResponse(
            message="Report submitted successfully",
            verification_status=evaluation["status"],
            report=report_data,
        )
    except SQLAlchemyError as exc:
        logger.error(f"Failed to create report: {exc}")
        raise HTTPException(
            status_code=500, detail="Database is unavailable") from exc
