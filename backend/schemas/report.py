from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator, validator


ALLOWED_CATEGORIES = {
    'Roads': [
        'Pothole',
        'Road flooding',
        'Fallen tree',
        'Road obstruction',
        'Damaged road surface',
    ],
    'Lighting': [
        'Streetlight outage',
        'Damaged light pole',
        'Exposed wiring',
        'Multiple lights out',
    ],
    'Waste': [
        'Overflowing bin',
        'Illegal dumping',
        'Uncollected waste',
        'Blocked drainage',
        'Hazardous waste',
    ],
}

ALLOWED_SEVERITIES = {'Low', 'Medium', 'High', 'Critical'}


class ReportSummary(BaseModel):
    report_id: str
    category: Optional[str]
    issue_type: Optional[str]
    zone: Optional[str]
    reported_time: Optional[datetime]
    location_status: Optional[str]
    freshness_status: Optional[str]

    model_config = {
        "from_attributes": True,
    }


class ReportDetail(ReportSummary):
    description: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    citizen_severity: Optional[str]
    corroborating_reports: Optional[int]
    conflicting_evidence: Optional[str]
    created_at: datetime
    incident_id: Optional[str]
    priority_score: Optional[int] = None
    priority_level: Optional[str] = None
    confidence_score: Optional[int] = None
    confidence_level: Optional[str] = None
    verification_status: Optional[str] = None
    human_status: Optional[str] = None
    incident_updated_at: Optional[datetime] = None


class RecentReportItem(BaseModel):
    report_id: str
    category: Optional[str] = None
    issue_type: Optional[str] = None
    description: Optional[str] = None
    zone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    citizen_severity: Optional[str] = None
    reported_time: Optional[datetime] = None
    created_at: Optional[datetime] = None
    location_status: Optional[str] = None
    freshness_status: Optional[str] = None

    # Incident relationship attributes
    incident_id: Optional[str] = None
    relationship_type: str  # "Attached to Incident INC-XXXXX" / "New Incident Created: INC-XXXXX" / "Awaiting Incident Assignment"
    total_incident_reports: Optional[int] = 0

    # Canonical evaluated incident attributes
    priority_score: Optional[int] = None
    priority_level: Optional[str] = None
    confidence_score: Optional[int] = None
    confidence_level: Optional[str] = None
    verification_status: Optional[str] = None

    model_config = {
        "from_attributes": True,
    }



class ReportCreate(BaseModel):
    category: str
    issue_type: str
    description: str
    zone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    citizen_severity: str

    @validator('category')
    def validate_category(cls, value):
        if value not in ALLOWED_CATEGORIES:
            raise ValueError('category must be one of: Roads, Lighting, Waste')
        return value

    @validator('issue_type')
    def validate_issue_type(cls, value):
        if not value or not value.strip():
            raise ValueError('issue_type is required')
        return value.strip()

    @validator('description')
    def validate_description(cls, value):
        if value is None:
            raise ValueError('description is required')
        normalized = value.strip()
        if len(normalized) < 10:
            raise ValueError('description must be at least 10 characters')
        if len(normalized) > 2000:
            raise ValueError('description is too long')
        return normalized

    @validator('citizen_severity')
    def validate_severity(cls, value):
        if value not in ALLOWED_SEVERITIES:
            raise ValueError('citizen_severity must be one of: Low, Medium, High, Critical')
        return value

    @validator('latitude')
    def validate_latitude(cls, value):
        if value is None:
            return value
        if value < -90 or value > 90:
            raise ValueError('latitude must be between -90 and 90')
        return value

    @validator('longitude')
    def validate_longitude(cls, value):
        if value is None:
            return value
        if value < -180 or value > 180:
            raise ValueError('longitude must be between -180 and 180')
        return value

    @model_validator(mode='after')
    def validate_issue_type_matches_category(cls, values):
        category = values.category
        issue_type = values.issue_type
        if category and issue_type:
            allowed = ALLOWED_CATEGORIES.get(category, [])
            if issue_type not in allowed:
                raise ValueError(f'issue_type must be valid for category {category}')
        return values

    @model_validator(mode='after')
    def validate_coordinate_pair(cls, values):
        latitude = values.latitude
        longitude = values.longitude
        if (latitude is None) ^ (longitude is None):
            raise ValueError('latitude and longitude must both be provided or both omitted')
        return values


class ReportListMetadata(BaseModel):
    items: List[ReportSummary]
    page: int
    page_size: int
    total: int
    total_pages: int


class ReportCreateResponse(BaseModel):
    message: str
    verification_status: str
    report: ReportDetail

    model_config = {
        "from_attributes": True,
    }
