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
    Incident,
    IncidentReport,
    Report,
    ExternalEvidence,
    ResponderVerification,
)


class TestOfficerDashboardAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = SessionLocal()

        # Clean any prior test records before seeding
        cls.cleanup_test_records()
        # Seed test data for dashboard verification
        cls.seed_test_incidents()

    @classmethod
    def tearDownClass(cls):
        cls.cleanup_test_records()
        cls.db.close()

    @classmethod
    def cleanup_test_records(cls):
        try:
            test_reports = cls.db.query(Report).filter(Report.report_id.like("RPT-DASH-%")).all()
            for r in test_reports:
                cls.db.delete(r)
            test_incidents = cls.db.query(Incident).filter(Incident.incident_id.like("INC-DASH-%")).all()
            for inc in test_incidents:
                cls.db.delete(inc)
            cls.db.commit()
        except Exception:
            cls.db.rollback()


    @classmethod
    def seed_test_incidents(cls):
        now = datetime.utcnow()

        # 1. Critical Corroborated Incident (Multiple reports, Roads, Pothole, North Zone)
        inc_crit = Incident(
            incident_id="INC-DASH-CRIT",
            category="Roads",
            issue_type="Road flooding",
            zone="North",
            status="Pending",
        )
        cls.db.add(inc_crit)
        cls.db.flush()

        for i in range(3):
            rep = Report(
                report_id=f"RPT-DASH-CRIT-{i+1}",
                category="Roads",
                issue_type="Road flooding",
                description=f"Severe flooding on main artery road, report #{i+1}",
                zone="North",
                latitude=11.0168 + (i * 0.001),
                longitude=76.9558,
                reported_time=now - timedelta(minutes=20 - (i * 5)),
                citizen_severity="Critical",
                location_status="Available",
                freshness_status="Fresh",
            )
            cls.db.add(rep)
            cls.db.flush()
            link = IncidentReport(incident_id=inc_crit.id, report_id=rep.id)
            cls.db.add(link)

        # 2. Officially Verified Incident (Lighting, Streetlight outage, South Zone)
        inc_ver = Incident(
            incident_id="INC-DASH-VER",
            category="Lighting",
            issue_type="Streetlight outage",
            zone="South",
            status="Pending",
        )
        cls.db.add(inc_ver)
        cls.db.flush()

        rep_ver = Report(
            report_id="RPT-DASH-VER-1",
            category="Lighting",
            issue_type="Streetlight outage",
            description="Dark stretch of road due to outage",
            zone="South",
            latitude=11.0120,
            longitude=76.9510,
            reported_time=now - timedelta(hours=2),
            citizen_severity="Medium",
            location_status="Available",
            freshness_status="Fresh",
        )
        cls.db.add(rep_ver)
        cls.db.flush()
        link_ver = IncidentReport(incident_id=inc_ver.id, report_id=rep_ver.id)
        cls.db.add(link_ver)

        resp_ver = ResponderVerification(
            incident_id=inc_ver.id,
            responder_id=101,
            verification_status="Verified",
            notes="Electrician inspected lamp post and confirmed fuse issue.",
            verified_at=now - timedelta(hours=1),
        )
        cls.db.add(resp_ver)

        # 3. Conflicted Incident (Waste, Illegal dumping, East Zone)
        inc_conf = Incident(
            incident_id="INC-DASH-CONF",
            category="Waste",
            issue_type="Illegal dumping",
            zone="East",
            status="Pending",
        )
        cls.db.add(inc_conf)
        cls.db.flush()

        rep_conf = Report(
            report_id="RPT-DASH-CONF-1",
            category="Waste",
            issue_type="Illegal dumping",
            description="Dumping of hazardous waste reported",
            zone="East",
            latitude=11.0250,
            longitude=76.9650,
            reported_time=now - timedelta(hours=5),
            citizen_severity="High",
            location_status="Available",
            freshness_status="Fresh",
            conflicting_evidence="Yes",
        )
        cls.db.add(rep_conf)
        cls.db.flush()
        link_conf = IncidentReport(incident_id=inc_conf.id, report_id=rep_conf.id)
        cls.db.add(link_conf)

        # 4. Stale Incident (Roads, Damaged road surface, Central Zone, >72h old)
        inc_stale = Incident(
            incident_id="INC-DASH-STALE",
            category="Roads",
            issue_type="Damaged road surface",
            zone="Central",
            status="Pending",
        )
        cls.db.add(inc_stale)
        cls.db.flush()

        rep_stale = Report(
            report_id="RPT-DASH-STALE-1",
            category="Roads",
            issue_type="Damaged road surface",
            description="Old road damage not yet resolved",
            zone="Central",
            latitude=11.0180,
            longitude=76.9530,
            reported_time=now - timedelta(hours=96),
            citizen_severity="Medium",
            location_status="Available",
            freshness_status="Stale",
        )
        cls.db.add(rep_stale)
        cls.db.flush()
        link_stale = IncidentReport(incident_id=inc_stale.id, report_id=rep_stale.id)
        cls.db.add(link_stale)

        # 5. Missing Coordinates Incident (Waste, Overflowing bin, West Zone)
        inc_nocoord = Incident(
            incident_id="INC-DASH-NOCOORD",
            category="Waste",
            issue_type="Overflowing bin",
            zone="West",
            status="Pending",
        )
        cls.db.add(inc_nocoord)
        cls.db.flush()

        rep_nocoord = Report(
            report_id="RPT-DASH-NOCOORD-1",
            category="Waste",
            issue_type="Overflowing bin",
            description="Bin overflowing near commercial block",
            zone="West",
            latitude=None,
            longitude=None,
            reported_time=now - timedelta(hours=1),
            citizen_severity="Low",
            location_status="Missing",
            freshness_status="Fresh",
        )
        cls.db.add(rep_nocoord)
        cls.db.flush()
        link_nocoord = IncidentReport(incident_id=inc_nocoord.id, report_id=rep_nocoord.id)
        cls.db.add(link_nocoord)
        cls.db.commit()


        # Run VerificationEngine update_evaluation_labels on all seeded test incidents
        from services.verification_engine import VerificationEngine
        for inc_id in ["INC-DASH-CRIT", "INC-DASH-VER", "INC-DASH-CONF", "INC-DASH-STALE", "INC-DASH-NOCOORD"]:
            inc = cls.db.query(Incident).filter(Incident.incident_id == inc_id).scalar()
            reps = (
                cls.db.query(Report)
                .join(IncidentReport, Report.id == IncidentReport.report_id)
                .filter(IncidentReport.incident_id == inc.id)
                .all()
            )
            verifs = cls.db.query(ResponderVerification).filter(ResponderVerification.incident_id == inc.id).all()
            engine = VerificationEngine(db=cls.db, incident=inc, reports=reps, verifications=verifs)
            engine.update_evaluation_labels()
        cls.db.commit()


    def test_get_dashboard_stats(self):
        """Test GET /api/incidents/stats returns correct KPI aggregates."""
        response = self.client.get("/api/incidents/stats")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("total_incidents", data)
        self.assertIn("critical_incidents", data)
        self.assertIn("high_priority_incidents", data)
        self.assertIn("corroborated_incidents", data)
        self.assertIn("verified_incidents", data)
        self.assertIn("pending_incidents", data)
        self.assertIn("conflicted_incidents", data)
        self.assertIn("stale_incidents", data)

        self.assertGreaterEqual(data["total_incidents"], 5)
        self.assertGreaterEqual(data["critical_incidents"], 1)
        self.assertGreaterEqual(data["verified_incidents"], 1)
        self.assertGreaterEqual(data["conflicted_incidents"], 1)
        self.assertGreaterEqual(data["stale_incidents"], 1)

    def test_list_incidents_priority_sorting(self):
        """Test GET /api/incidents sorts primarily by priority_score descending."""
        response = self.client.get("/api/incidents")
        self.assertEqual(response.status_code, 200)
        items = response.json()
        self.assertIsInstance(items, list)
        self.assertGreaterEqual(len(items), 5)

        # Check descending order of priority score
        scores = [item["priority_score"] for item in items]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_filter_by_category(self):
        """Test filtering by category (e.g. Roads, Lighting, Waste)."""
        response = self.client.get("/api/incidents?category=Lighting")
        self.assertEqual(response.status_code, 200)
        items = response.json()
        for item in items:
            self.assertEqual(item["category"], "Lighting")

    def test_filter_by_status(self):
        """Test filtering by verification status (e.g. Verified, Conflicted)."""
        response = self.client.get("/api/incidents?status=Verified")
        self.assertEqual(response.status_code, 200)
        items = response.json()
        for item in items:
            self.assertEqual(item["status"], "Verified")

    def test_filter_by_freshness(self):
        """Test filtering by freshness (e.g. Stale)."""
        response = self.client.get("/api/incidents?freshness=Stale")
        self.assertEqual(response.status_code, 200)
        items = response.json()
        for item in items:
            self.assertEqual(item["freshness"], "Stale")

    def test_search_functionality(self):
        """Test keyword searching across Incident ID and category/issue."""
        response = self.client.get("/api/incidents?search=INC-DASH-CRIT")
        self.assertEqual(response.status_code, 200)
        items = response.json()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["incident_id"], "INC-DASH-CRIT")

    def test_search_by_report_id(self):
        """Test searching by Report ID returns the associated parent incident."""
        response = self.client.get("/api/incidents?search=RPT-DASH-CRIT-1")
        self.assertEqual(response.status_code, 200)
        items = response.json()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["incident_id"], "INC-DASH-CRIT")
        self.assertEqual(items[0]["category"], "Roads")

    def test_search_by_report_id_case_insensitive(self):
        """Test searching by lowercase Report ID returns the associated parent incident."""
        response = self.client.get("/api/incidents?search=rpt-dash-crit-1")
        self.assertEqual(response.status_code, 200)
        items = response.json()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["incident_id"], "INC-DASH-CRIT")

    def test_search_by_invalid_report_id(self):
        """Test searching by non-existent Report ID returns 0 incidents."""
        response = self.client.get("/api/incidents?search=RPT-NONEXISTENT-999")
        self.assertEqual(response.status_code, 200)
        items = response.json()
        self.assertEqual(len(items), 0)

    def test_unassociated_orphan_report_lookup(self):
        """Test looking up an unassociated report returns report data with incident_id=None."""
        now = datetime.utcnow()
        orphan_rep = Report(
            report_id="RPT-DASH-ORPHAN-1",
            category="Waste",
            issue_type="Overflowing bin",
            description="Unassociated test orphan report",
            zone="West",
            reported_time=now,
            citizen_severity="Low",
            location_status="Missing",
            freshness_status="Fresh",
        )
        self.db.add(orphan_rep)
        self.db.commit()

        # Search in incidents queue should be empty
        resp_inc = self.client.get("/api/incidents?search=RPT-DASH-ORPHAN-1")
        self.assertEqual(resp_inc.status_code, 200)
        self.assertEqual(len(resp_inc.json()), 0)

        # Lookup in reports API returns report with incident_id=None
        resp_rep = self.client.get("/api/reports/RPT-DASH-ORPHAN-1")
        self.assertEqual(resp_rep.status_code, 200)
        self.assertIsNone(resp_rep.json()["incident_id"])


    def test_incident_drilldown_verified(self):
        """Test drill-down for verified incident with responder record."""
        response = self.client.get("/api/incidents/INC-DASH-VER")
        self.assertEqual(response.status_code, 200)
        detail = response.json()

        self.assertEqual(detail["incident_id"], "INC-DASH-VER")
        self.assertEqual(detail["status"], "Verified")
        self.assertEqual(detail["confidence_score"], 100)
        self.assertIn("Verified incident", detail["recommended_action"])

        # Check responder verification list
        self.assertEqual(len(detail["responder_verifications"]), 1)
        self.assertEqual(detail["responder_verifications"][0]["verification_status"], "Verified")

        # Check explanations
        self.assertTrue(len(detail["confidence_explanations"]) > 0)
        self.assertTrue(len(detail["priority_explanations"]) > 0)


    def test_incident_drilldown_conflicted(self):
        """Test drill-down for conflicted incident."""
        response = self.client.get("/api/incidents/INC-DASH-CONF")
        self.assertEqual(response.status_code, 200)
        detail = response.json()

        self.assertEqual(detail["status"], "Conflicted")
        self.assertIn("Manual verification required", detail["recommended_action"])

    def test_incident_drilldown_missing_location(self):
        """Test drill-down for incident with missing coordinates."""
        response = self.client.get("/api/incidents/INC-DASH-NOCOORD")
        self.assertEqual(response.status_code, 200)
        detail = response.json()

        self.assertIsNone(detail["latitude"])
        self.assertIsNone(detail["longitude"])
        self.assertEqual(detail["status"], "Unknown")
        self.assertEqual(len(detail["reports"]), 1)
        self.assertEqual(detail["reports"][0]["location_status"], "Missing")

    def test_drilldown_not_found(self):
        """Test 404 response for non-existent incident ID."""
        response = self.client.get("/api/incidents/INC-NONEXISTENT-999")
        self.assertEqual(response.status_code, 404)

    def test_map_coordinate_payload_and_unmapped_handling(self):
        """Verify spatial fields required by Leaflet IncidentMap component."""
        response = self.client.get("/api/incidents?search=INC-DASH-CRIT")
        self.assertEqual(response.status_code, 200)
        items = response.json()
        mapped = next((inc for inc in items if inc["incident_id"] == "INC-DASH-CRIT"), None)
        self.assertIsNotNone(mapped)
        self.assertIsInstance(mapped["latitude"], (int, float))
        self.assertIsInstance(mapped["longitude"], (int, float))
        self.assertGreater(mapped["latitude"], 10.0)
        self.assertGreater(mapped["longitude"], 70.0)
        self.assertIn("priority_score", mapped)
        self.assertIn("confidence_score", mapped)
        self.assertIn("status", mapped)
        self.assertIn("freshness", mapped)

        # Find unmapped incident
        resp_unmapped = self.client.get("/api/incidents?search=INC-DASH-NOCOORD")
        self.assertEqual(resp_unmapped.status_code, 200)
        unmapped_items = resp_unmapped.json()
        unmapped = next((inc for inc in unmapped_items if inc["incident_id"] == "INC-DASH-NOCOORD"), None)
        self.assertIsNotNone(unmapped)
        self.assertIsNone(unmapped["latitude"])
        self.assertIsNone(unmapped["longitude"])

    def test_recent_reports_endpoint(self):
        """Test GET /api/reports/recent returns newest reports first within limit."""
        response = self.client.get("/api/reports/recent?limit=5")
        self.assertEqual(response.status_code, 200)
        items = response.json()
        self.assertLessEqual(len(items), 5)
        self.assertGreater(len(items), 0)

        # Check sorting by created_at desc
        for i in range(len(items) - 1):
            t1 = items[i].get("created_at") or items[i].get("reported_time")
            t2 = items[i + 1].get("created_at") or items[i + 1].get("reported_time")
            if t1 and t2:
                self.assertGreaterEqual(t1, t2)

    def test_recent_reports_relationship_types(self):
        """Test that report relationship types distinguish between New Incident, Attached, and Unassigned."""
        # Create an orphan report without incident
        orphan = Report(
            report_id="RPT-DASH-ORPHAN-RECENT",
            category="Lighting",
            issue_type="Streetlight outage",
            description="Recent orphan test report description",
            zone="Central",
            reported_time=datetime.utcnow(),
            citizen_severity="Medium",
            location_status="Available",
            freshness_status="Fresh",
        )
        self.db.add(orphan)
        self.db.commit()

        response = self.client.get("/api/reports/recent?limit=20")
        self.assertEqual(response.status_code, 200)
        items = response.json()

        orphan_item = next((r for r in items if r["report_id"] == "RPT-DASH-ORPHAN-RECENT"), None)
        self.assertIsNotNone(orphan_item)
        self.assertEqual(orphan_item["relationship_type"], "Awaiting Incident Assignment")
        self.assertIsNone(orphan_item["incident_id"])

        # Check multi-report incident attachment vs single report creation
        crit_rep2 = next((r for r in items if r["report_id"] == "RPT-DASH-CRIT-2"), None)
        if crit_rep2:
            self.assertIn("Attached to Incident INC-DASH-CRIT", crit_rep2["relationship_type"])

    def test_new_report_submission_reflects_in_recent_reports(self):
        """Test submitting a new report immediately appears as first recent report."""
        post_payload = {
            "category": "Roads",
            "issue_type": "Pothole",
            "description": "Newly submitted road pothole requiring municipal assessment.",
            "zone": "North",
            "citizen_severity": "High",
            "latitude": 11.018,
            "longitude": 76.965,
        }
        create_resp = self.client.post("/api/reports", json=post_payload)
        self.assertEqual(create_resp.status_code, 201)
        created_data = create_resp.json()
        new_report_id = created_data["report"]["report_id"]

        # Fetch recent reports
        recent_resp = self.client.get("/api/reports/recent?limit=5")
        self.assertEqual(recent_resp.status_code, 200)
        recent_items = recent_resp.json()

        self.assertEqual(recent_items[0]["report_id"], new_report_id)
        self.assertEqual(recent_items[0]["category"], "Roads")
        self.assertEqual(recent_items[0]["issue_type"], "Pothole")
        self.assertIsNotNone(recent_items[0]["incident_id"])


if __name__ == "__main__":
    unittest.main()

