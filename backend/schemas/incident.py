from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class IncidentStats(BaseModel):
    total_incidents: int
    critical_incidents: int
    high_priority_incidents: int
    corroborated_incidents: int
    verified_incidents: int
    pending_incidents: int
    conflicted_incidents: int
    stale_incidents: int


class IncidentOfficerSummary(BaseModel):
    incident_id: str
    category: Optional[str] = None
    issue_type: Optional[str] = None
    zone: Optional[str] = None
    status: Optional[str] = None
    human_status: str = "Awaiting Review"
    priority_score: int = 0
    priority_level: str = "Low"
    confidence_score: int = 0
    confidence_level: str = "Low"
    freshness: str = "Unknown"
    total_reports_count: int = 0
    independent_reports_count: int = 0
    duplicate_reports_count: int = 0
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    last_reported_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }


class ExternalEvidenceItem(BaseModel):
    id: int
    evidence_id: Optional[str] = None
    incident_id: int
    report_id: Optional[int] = None
    source_type: Optional[str] = None
    source_status: Optional[str] = None
    observed_at: Optional[datetime] = None
    freshness_status: Optional[str] = None
    details: Optional[str] = None
    filename: Optional[str] = None
    file_url: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }



class ResponderVerificationItem(BaseModel):
    id: int
    incident_id: int
    responder_id: Optional[int] = None
    responder_name: Optional[str] = None
    verification_status: Optional[str] = None
    notes: Optional[str] = None
    verified_at: Optional[datetime] = None
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }


class ResponderVerificationCreate(BaseModel):
    decision: str
    rationale: str = Field(..., min_length=1)
    responder_name: str


    model_config = {
        "from_attributes": True,
    }


class ReportItem(BaseModel):
    id: int
    report_id: str
    category: Optional[str] = None
    issue_type: Optional[str] = None
    description: Optional[str] = None
    zone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    reported_time: Optional[datetime] = None
    citizen_severity: Optional[str] = None
    location_status: Optional[str] = None
    freshness_status: Optional[str] = None
    conflicting_evidence: Optional[str] = None
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }


class IncidentOfficerDetail(IncidentOfficerSummary):
    confidence_explanations: List[str] = Field(default_factory=list)
    priority_explanations: List[str] = Field(default_factory=list)
    recommended_action: str = ""
    reports: List[ReportItem] = Field(default_factory=list)
    evidence: List[ExternalEvidenceItem] = Field(default_factory=list)
    responder_verifications: List[ResponderVerificationItem] = Field(default_factory=list)


# Backwards compatibility schemas
class IncidentSummary(BaseModel):
    incident_id: str
    category: Optional[str] = None
    issue_type: Optional[str] = None
    zone: Optional[str] = None
    status: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }


class IncidentDetail(IncidentSummary):
    reports: List[str] = Field(default_factory=list)

