import io
import os
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import app
from database.connection import SessionLocal
from models.models import (
    ExternalEvidence,
    Incident,
    IncidentReport,
    Report,
)


class TestEvidenceManagement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = SessionLocal()
        cls.cleanup_test_records()
        cls.seed_test_incident()

    @classmethod
    def tearDownClass(cls):
        cls.cleanup_test_records()
        cls.db.close()

    @classmethod
    def cleanup_test_records(cls):
        try:
            # Delete test evidence
            cls.db.query(ExternalEvidence).filter(
                ExternalEvidence.source_type.like("Test%") | ExternalEvidence.details.like("Test%")
            ).delete()
            # Delete test reports and incidents
            reports = cls.db.query(Report).filter(Report.report_id.like("RPT-EVD-TEST%")).all()
            for r in reports:
                cls.db.delete(r)
            incidents = cls.db.query(Incident).filter(Incident.incident_id.like("INC-EVD-TEST%")).all()
            for inc in incidents:
                cls.db.delete(inc)
            cls.db.commit()
        except Exception:
            cls.db.rollback()

    @classmethod
    def seed_test_incident(cls):
        now = datetime.utcnow()
        inc = Incident(
            incident_id="INC-EVD-TEST-1",
            category="Roads",
            issue_type="Major pothole",
            zone="North",
            status="Pending",
        )
        cls.db.add(inc)
        cls.db.flush()

        rep = Report(
            report_id="RPT-EVD-TEST-1",
            category="Roads",
            issue_type="Major pothole",
            description="Deep pothole in middle of lane",
            zone="North",
            latitude=11.0168,
            longitude=76.9558,
            reported_time=now - timedelta(hours=2),
            citizen_severity="Medium",
            location_status="Available",
            freshness_status="Fresh",
        )
        cls.db.add(rep)
        cls.db.flush()

        link = IncidentReport(incident_id=inc.id, report_id=rep.id)
        cls.db.add(link)
        cls.db.commit()

        # Seed incident with no evidence
        inc_noevd = Incident(
            incident_id="INC-EVD-TEST-NOEVD",
            category="Lighting",
            issue_type="Streetlight flickering",
            zone="South",
            status="Pending",
        )
        cls.db.add(inc_noevd)
        cls.db.flush()

        rep_noevd = Report(
            report_id="RPT-EVD-TEST-NOEVD-1",
            category="Lighting",
            issue_type="Streetlight flickering",
            description="Light flickering continuously",
            zone="South",
            latitude=11.0120,
            longitude=76.9510,
            reported_time=now - timedelta(hours=3),
            citizen_severity="Low",
            location_status="Available",
            freshness_status="Fresh",
        )
        cls.db.add(rep_noevd)
        cls.db.flush()

        link_noevd = IncidentReport(incident_id=inc_noevd.id, report_id=rep_noevd.id)
        cls.db.add(link_noevd)
        cls.db.commit()

        from services.verification_engine import VerificationEngine
        engine = VerificationEngine(db=cls.db, incident=inc, reports=[rep])
        engine.update_evaluation_labels()

        engine_noevd = VerificationEngine(db=cls.db, incident=inc_noevd, reports=[rep_noevd])
        engine_noevd.update_evaluation_labels()
        cls.db.commit()



    def test_attach_simulated_evidence_json(self):
        """Test creating evidence with JSON simulated metadata."""
        payload = {
            "source_type": "IoT/Sensor",
            "source_status": "High Quality",
            "observed_at": datetime.utcnow().isoformat(),
            "latitude": 11.0169,
            "longitude": 76.9559,
            "details": "Test road acoustic vibration sensor reading.",
        }
        res = self.client.post("/api/incidents/INC-EVD-TEST-1/evidence", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["source_type"], "IoT/Sensor")
        self.assertEqual(data["source_status"], "High Quality")
        self.assertEqual(data["freshness_status"], "Fresh")
        self.assertIsNotNone(data["evidence_id"])
        self.assertAlmostEqual(data["latitude"], 11.0169)

    def test_attach_image_evidence_multipart(self):
        """Test creating evidence with valid image upload."""
        dummy_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        files = {"file": ("pothole_proof.png", io.BytesIO(dummy_png), "image/png")}
        form_data = {
            "source_type": "Citizen",
            "source_status": "Standard",
            "details": "Test citizen uploaded pothole photograph.",
            "latitude": "11.0168",
            "longitude": "76.9558",
        }
        res = self.client.post("/api/incidents/INC-EVD-TEST-1/evidence", data=form_data, files=files)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["filename"], "pothole_proof.png")
        self.assertIn("/uploads/evidence/", data["file_url"])
        self.assertEqual(data["mime_type"], "image/png")

    def test_unsupported_file_extension(self):
        """Test uploading unsupported file format (.txt) returns 400 Bad Request."""
        dummy_txt = b"This is not an image."
        files = {"file": ("script.exe", io.BytesIO(dummy_txt), "image/png")}
        res = self.client.post("/api/incidents/INC-EVD-TEST-1/evidence", files=files)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Unsupported file type", res.json()["detail"])

    def test_unsupported_mime_type(self):
        """Test uploading wrong MIME type returns 400 Bad Request."""
        dummy_data = b"Some data"
        files = {"file": ("document.png", io.BytesIO(dummy_data), "application/pdf")}
        res = self.client.post("/api/incidents/INC-EVD-TEST-1/evidence", files=files)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Unsupported MIME type", res.json()["detail"])

    def test_oversized_file_upload(self):
        """Test upload exceeding 10MB limit returns 413 Payload Too Large."""
        large_data = b"0" * (11 * 1024 * 1024)  # 11 MB
        files = {"file": ("huge_image.jpg", io.BytesIO(large_data), "image/jpeg")}
        res = self.client.post("/api/incidents/INC-EVD-TEST-1/evidence", files=files)
        self.assertEqual(res.status_code, 413)

    def test_attach_evidence_invalid_incident(self):
        """Test attaching evidence to non-existent incident returns 404."""
        res = self.client.post("/api/incidents/INC-DOES-NOT-EXIST/evidence", json={"source_type": "Citizen"})
        self.assertEqual(res.status_code, 404)

    def test_get_incident_evidence_list(self):
        """Test GET /api/incidents/{incident_id}/evidence returns attached items."""
        res = self.client.get("/api/incidents/INC-EVD-TEST-1/evidence")
        self.assertEqual(res.status_code, 200)
        items = res.json()
        self.assertIsInstance(items, list)
        self.assertGreaterEqual(len(items), 1)

    def test_evidence_missing_location(self):
        """Test evidence with missing location coordinates explicitly returns None."""
        payload = {
            "source_type": "CCTV",
            "source_status": "Standard",
            "details": "Test camera without GPS coordinates.",
            "latitude": None,
            "longitude": None,
        }
        res = self.client.post("/api/incidents/INC-EVD-TEST-1/evidence", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertIsNone(data["latitude"])
        self.assertIsNone(data["longitude"])

    def test_verification_confidence_boost_from_evidence(self):
        """Verify that adding external evidence boosts incident confidence in drill-down."""
        res_drilldown = self.client.get("/api/incidents/INC-EVD-TEST-1")
        self.assertEqual(res_drilldown.status_code, 200)
        detail = res_drilldown.json()
        self.assertGreater(detail["confidence_score"], 10)
        # Check that confidence explanations include external evidence
        has_evidence_exp = any("External Evidence" in exp for exp in detail["confidence_explanations"])
        self.assertTrue(has_evidence_exp)

    def test_delete_evidence(self):
        """Test deleting evidence adjusts records and scores."""
        # Create evidence to delete
        payload = {
            "source_type": "Field Responder",
            "source_status": "Standard",
            "details": "Test temporary evidence item.",
        }
        create_res = self.client.post("/api/incidents/INC-EVD-TEST-1/evidence", json=payload)
        self.assertEqual(create_res.status_code, 201)
        evd_id = create_res.json()["evidence_id"]

        # Delete it
        del_res = self.client.delete(f"/api/evidence/{evd_id}")
        self.assertEqual(del_res.status_code, 200)
        self.assertIn("deleted successfully", del_res.json()["message"])

    def test_duplicate_evidence_handling(self):
        """Test attaching identical evidence is handled idempotently without duplicate record creation."""
        payload = {
            "source_type": "CCTV",
            "source_status": "Standard",
            "details": "Unique identical CCTV frame detail string for duplication test.",
        }
        res1 = self.client.post("/api/incidents/INC-EVD-TEST-1/evidence", json=payload)
        self.assertEqual(res1.status_code, 201)
        evd1_id = res1.json()["evidence_id"]

        res2 = self.client.post("/api/incidents/INC-EVD-TEST-1/evidence", json=payload)
        self.assertEqual(res2.status_code, 201)
        evd2_id = res2.json()["evidence_id"]
        # Both calls return the same evidence record
        self.assertEqual(evd1_id, evd2_id)

    def test_drilldown_evidence_payload(self):
        """Test that drill-down GET /api/incidents/{id} includes evidence list with all metadata."""
        res = self.client.get("/api/incidents/INC-EVD-TEST-1")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("evidence", data)
        self.assertIsInstance(data["evidence"], list)
        self.assertGreaterEqual(len(data["evidence"]), 1)
        evd = data["evidence"][0]
        self.assertIn("source_type", evd)
        self.assertIn("source_status", evd)
        self.assertIn("freshness_status", evd)
        self.assertIn("details", evd)

    def test_stale_corroborating_evidence(self):
        """Test evidence with an old observed timestamp is marked as Stale."""
        stale_date = datetime.utcnow() - timedelta(days=5)
        payload = {
            "source_type": "Citizen",
            "source_status": "Standard",
            "observed_at": stale_date.isoformat(),
            "details": "Test stale evidence.",
        }
        res = self.client.post("/api/incidents/INC-EVD-TEST-1/evidence", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["freshness_status"], "Stale")

    def test_drilldown_without_evidence(self):
        """Test that incident with no evidence returns empty evidence list."""
        res = self.client.get("/api/incidents/INC-EVD-TEST-NOEVD")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["evidence"], [])



if __name__ == "__main__":
    unittest.main()

