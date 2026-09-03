import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import app
from database.connection import engine
from database.base import Base
from sqlalchemy.orm import sessionmaker
from models.models import Incident, Report, IncidentReport

# We'll use the existing test client setup
client = TestClient(app)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    # Not dropping since we are testing against the main DB in this environment typically,
    # or the test runner handles it. We will clean up after tests anyway.

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

class TestPhase2Verification:
    def _create_mock_incident(self, db_session):
        import uuid
        from datetime import datetime
        inc_id = f"INC-TEST-{uuid.uuid4().hex[:8]}"
        incident = Incident(
            incident_id=inc_id,
            status="Pending",
            human_status="Awaiting Review",
            category="Test",
            priority_score=10,
            confidence_score=10
        )
        db_session.add(incident)
        db_session.commit()
        db_session.refresh(incident)
        return incident

    def test_submit_verify_decision(self, db_session):
        incident = self._create_mock_incident(db_session)
        payload = {
            "decision": "VERIFY",
            "rationale": "Looks verified to me",
            "responder_name": "Officer Smith"
        }
        resp = client.post(f"/api/incidents/{incident.incident_id}/verification", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["verification_status"] == "Verified"
        assert data["responder_name"] == "Officer Smith"

        # Check that the incident human_status updated
        db_session.refresh(incident)
        assert incident.human_status == "Verified"

        # Note: Depending on reports, canonical status might also be Verified
        assert incident.status in ["Verified", "Pending", "Unknown"]

    def test_submit_reject_decision(self, db_session):
        incident = self._create_mock_incident(db_session)
        payload = {
            "decision": "REJECT",
            "rationale": "False alarm",
            "responder_name": "Officer Jones"
        }
        resp = client.post(f"/api/incidents/{incident.incident_id}/verification", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["verification_status"] == "Rejected"
        
        db_session.refresh(incident)
        assert incident.human_status == "Rejected"
        assert incident.status == "Rejected" # Engine overrides to Rejected

    def test_submit_escalate_decision(self, db_session):
        incident = self._create_mock_incident(db_session)
        payload = {
            "decision": "ESCALATE",
            "rationale": "Need more info",
            "responder_name": "Officer Lee"
        }
        resp = client.post(f"/api/incidents/{incident.incident_id}/verification", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["verification_status"] == "Needs More Evidence"
        
        db_session.refresh(incident)
        assert incident.human_status == "Needs More Evidence"
        # The automated status should remain untouched by the Escalation, typically Pending or Unknown
        assert incident.status in ["Pending", "Unknown"]

    def test_invalid_decision(self, db_session):
        incident = self._create_mock_incident(db_session)
        payload = {
            "decision": "INVALID_DECISION",
            "rationale": "Test",
            "responder_name": "Officer X"
        }
        resp = client.post(f"/api/incidents/{incident.incident_id}/verification", json=payload)
        assert resp.status_code == 400

    def test_empty_rationale(self, db_session):
        incident = self._create_mock_incident(db_session)
        payload = {
            "decision": "VERIFY",
            "rationale": "",
            "responder_name": "Officer Y"
        }
        resp = client.post(f"/api/incidents/{incident.incident_id}/verification", json=payload)
        assert resp.status_code == 422 # Pydantic validation error

    def test_incident_not_found(self):
        payload = {
            "decision": "VERIFY",
            "rationale": "Valid",
            "responder_name": "Officer Y"
        }
        resp = client.post(f"/api/incidents/INC-NON-EXISTENT/verification", json=payload)
        assert resp.status_code == 404
