from pydantic import BaseModel


class DatabaseStats(BaseModel):
    reports: int
    incidents: int
    external_evidence: int
    responder_verifications: int

    model_config = {
        "from_attributes": True,
    }
