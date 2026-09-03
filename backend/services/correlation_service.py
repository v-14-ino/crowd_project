from datetime import datetime, timedelta
from math import acos, atan2, cos, radians, sin, sqrt
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.models import Incident, IncidentReport, Report

EARTH_RADIUS_METERS = 6_371_000


class CorrelationSettings(BaseSettings):
    incident_time_threshold_minutes: int = Field(60, env='INCIDENT_TIME_THRESHOLD_MINUTES')
    incident_distance_threshold_meters: float = Field(200.0, env='INCIDENT_DISTANCE_THRESHOLD_METERS')

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')


settings = CorrelationSettings()


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points in meters."""
    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(max(0.0, 1 - a)))
    return EARTH_RADIUS_METERS * c


def _time_difference_minutes(first: datetime, second: datetime) -> float:
    return abs((first - second).total_seconds()) / 60.0


def reports_match(report_a: Report, report_b: Report) -> bool:
    if report_a.category != report_b.category:
        return False
    if report_a.issue_type != report_b.issue_type:
        return False
    if report_a.reported_time is None or report_b.reported_time is None:
        return False
    if _time_difference_minutes(report_a.reported_time, report_b.reported_time) > settings.incident_time_threshold_minutes:
        return False
    if report_a.latitude is None or report_a.longitude is None:
        return False
    if report_b.latitude is None or report_b.longitude is None:
        return False
    distance = haversine_distance_meters(
        report_a.latitude,
        report_a.longitude,
        report_b.latitude,
        report_b.longitude,
    )
    return distance <= settings.incident_distance_threshold_meters


def find_matching_incident(db: Session, report: Report) -> Optional[Incident]:
    if report.latitude is None or report.longitude is None or report.reported_time is None:
        return None

    time_lower = report.reported_time - timedelta(minutes=settings.incident_time_threshold_minutes)
    time_upper = report.reported_time + timedelta(minutes=settings.incident_time_threshold_minutes)

    candidate_incident_ids = db.execute(
        select(Incident.id)
        .join(IncidentReport, Incident.id == IncidentReport.incident_id)
        .join(Report, IncidentReport.report_id == Report.id)
        .where(
            Incident.category == report.category,
            Incident.issue_type == report.issue_type,
            Report.reported_time >= time_lower,
            Report.reported_time <= time_upper,
        )
        .distinct()
    ).scalars().all()

    if not candidate_incident_ids:
        return None

    for incident_id in candidate_incident_ids:
        existing_reports = db.execute(
            select(Report)
            .join(IncidentReport, Report.id == IncidentReport.report_id)
            .where(IncidentReport.incident_id == incident_id)
        ).scalars().all()

        for existing_report in existing_reports:
            if reports_match(report, existing_report):
                return db.get(Incident, incident_id)

    return None
