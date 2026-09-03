from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from schemas.incident import ExternalEvidenceItem


class EvidenceCreateRequest(BaseModel):
    source_type: str = Field(
        default="Citizen",
        description="Photo, Video reference, CCTV, IoT/Sensor, Citizen submission, Citizen, Municipal Officer, Field Responder, Simulated External Source",
    )
    source_status: str = Field(
        default="Standard",
        description="High Quality, Standard, Verified, Unverified",
    )
    observed_at: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    details: Optional[str] = None
    report_id: Optional[str] = None


class EvidenceResponse(ExternalEvidenceItem):
    pass


class EvidenceAttachResponse(ExternalEvidenceItem):
    previous_confidence_score: Optional[int] = None
    updated_confidence_score: int
    previous_priority_score: Optional[int] = None
    updated_priority_score: int
    previous_status: Optional[str] = None
    status: str
    freshness: str
    confidence_explanations: List[str] = Field(default_factory=list)
    priority_explanations: List[str] = Field(default_factory=list)
    recommended_action: str = ""

