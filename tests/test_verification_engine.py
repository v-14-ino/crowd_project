import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

# Ensure backend directory is in python path
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from models.models import (
    ExternalEvidence,
    Incident,
    Report,
    ResponderVerification,
)
from services.verification_engine import VerificationEngine


class TestVerificationEngine(unittest.TestCase):
    def setUp(self):
        self.ref_time = datetime(2026, 8, 18, 12, 0, 0)
        self.incident = Incident(
            id=1,
            incident_id="INC-TEST001",
            category="Roads",
            issue_type="Pothole",
            zone="North",
            status="Pending",
        )

    def test_single_report(self):
        """Single valid report with location and medium severity."""
        report = Report(
            id=101,
            report_id="RPT-001",
            category="Roads",
            issue_type="Pothole",
            description="Pothole near city center",
            zone="North",
            latitude=11.0168,
            longitude=76.9558,
            reported_time=self.ref_time - timedelta(hours=1),
            citizen_severity="Medium",
            location_status="Available",
            freshness_status="Fresh",
        )
        engine = VerificationEngine(
            incident=self.incident,
            reports=[report],
            reference_time=self.ref_time,
        )
        result = engine.evaluate_incident()

        # Confidence: Base 10 + 0 corroboration = 10 (Low)
        self.assertEqual(result["confidence_score"], 10)
        self.assertEqual(result["confidence_level"], "Low")
        # Verification status: Single uncorroborated report without responder -> Pending
        self.assertEqual(result["status"], "Pending")
        # Freshness: 1 hour old -> Fresh
        self.assertEqual(result["freshness"], "Fresh")
        # Priority: Medium (base 30) + conf_adj (10*0.2 = 2) = 32 (Medium)
        self.assertEqual(result["priority_score"], 32)
        self.assertEqual(result["priority_level"], "Medium")

    def test_multiple_corroborating_reports(self):
        """Multiple independent citizen reports within distance/time threshold."""
        # 3 independent reports ~60-80m apart, 15-20 mins apart
        r1 = Report(
            id=101,
            report_id="RPT-001",
            category="Roads",
            issue_type="Pothole",
            description="Pothole near north street",
            latitude=11.0168,
            longitude=76.9558,
            reported_time=self.ref_time - timedelta(minutes=45),
            citizen_severity="Medium",
        )
        r2 = Report(
            id=102,
            report_id="RPT-002",
            category="Roads",
            issue_type="Pothole",
            description="Deep pothole noticed here",
            latitude=11.0175,
            longitude=76.9558,
            reported_time=self.ref_time - timedelta(minutes=30),
            citizen_severity="High",
        )
        r3 = Report(
            id=103,
            report_id="RPT-003",
            category="Roads",
            issue_type="Pothole",
            description="Another citizen reporting pothole",
            latitude=11.0160,
            longitude=76.9558,
            reported_time=self.ref_time - timedelta(minutes=15),
            citizen_severity="Medium",
        )

        engine = VerificationEngine(
            incident=self.incident,
            reports=[r1, r2, r3],
            reference_time=self.ref_time,
        )
        result = engine.evaluate_incident()

        # 3 independent reports -> 2 corroborating reports (2 * 20 = +40) + base 10 = 50
        self.assertEqual(result["confidence_score"], 50)
        self.assertEqual(result["confidence_level"], "Medium")
        # Priority: High severity base 50 + impact 10 + conf_adj 10 = 70 (High)
        self.assertEqual(result["priority_score"], 70)
        self.assertEqual(result["priority_level"], "High")

    def test_obvious_duplicate_reports(self):
        """Duplicate reports at same location and time must not inflate confidence."""
        # 3 reports from exact same spot within 1 minute
        r1 = Report(
            id=101,
            report_id="RPT-001",
            category="Roads",
            issue_type="Pothole",
            description="Pothole here",
            latitude=11.016800,
            longitude=76.955800,
            reported_time=self.ref_time - timedelta(minutes=10),
            citizen_severity="Low",
        )
        r2 = Report(
            id=102,
            report_id="RPT-002",
            category="Roads",
            issue_type="Pothole",
            description="Pothole here duplicate submission",
            latitude=11.016802,
            longitude=76.955801,
            reported_time=self.ref_time - timedelta(minutes=10, seconds=15),
            citizen_severity="Low",
        )
        r3 = Report(
            id=103,
            report_id="RPT-003",
            category="Roads",
            issue_type="Pothole",
            description="Pothole click spam",
            latitude=11.016801,
            longitude=76.955803,
            reported_time=self.ref_time - timedelta(minutes=9, seconds=45),
            citizen_severity="Low",
        )

        engine = VerificationEngine(
            incident=self.incident,
            reports=[r1, r2, r3],
            reference_time=self.ref_time,
        )
        unique, dups = engine.cluster_independent_reports()
        self.assertEqual(len(unique), 1)
        self.assertEqual(len(dups), 2)

        result = engine.evaluate_incident()
        # Should only get base 10, no corroboration points (+0)
        self.assertEqual(result["confidence_score"], 10)
        self.assertTrue(any("duplicate" in exp.lower() for exp in result["confidence_explanations"]))

    def test_missing_location(self):
        """Missing location coordinates receives a penalty and marks status Unknown."""
        report = Report(
            id=101,
            report_id="RPT-001",
            category="Roads",
            issue_type="Pothole",
            description="Pothole somewhere on main road",
            latitude=None,
            longitude=None,
            reported_time=self.ref_time - timedelta(hours=1),
            citizen_severity="Low",
        )
        engine = VerificationEngine(
            incident=self.incident,
            reports=[report],
            reference_time=self.ref_time,
        )
        result = engine.evaluate_incident()

        # Base 10 - 30 (penalty) = clamped to 0
        self.assertEqual(result["confidence_score"], 0)
        self.assertEqual(result["status"], "Unknown")
        self.assertTrue(any("location penalty" in exp.lower() for exp in result["confidence_explanations"]))

    def test_conflicting_reports(self):
        """Conflicting reports apply penalty and result in Conflicted status."""
        r1 = Report(
            id=101,
            report_id="RPT-001",
            category="Roads",
            issue_type="Pothole",
            description="There is a pothole here",
            latitude=11.0168,
            longitude=76.9558,
            reported_time=self.ref_time - timedelta(hours=1),
            citizen_severity="High",
            conflicting_evidence="Yes",
        )
        engine = VerificationEngine(
            incident=self.incident,
            reports=[r1],
            reference_time=self.ref_time,
        )
        result = engine.evaluate_incident()

        # Status must be Conflicted
        self.assertEqual(result["status"], "Conflicted")
        # Conflict penalty applied
        self.assertTrue(any("conflict penalty" in exp.lower() for exp in result["confidence_explanations"]))

    def test_fresh_report(self):
        """Report <= 24 hours is Fresh with no priority penalty."""
        report = Report(
            id=101,
            report_id="RPT-001",
            category="Roads",
            issue_type="Pothole",
            description="Fresh report",
            latitude=11.0168,
            longitude=76.9558,
            reported_time=self.ref_time - timedelta(hours=3),
            citizen_severity="High",
        )
        engine = VerificationEngine(
            incident=self.incident,
            reports=[report],
            reference_time=self.ref_time,
        )
        result = engine.evaluate_incident()

        self.assertEqual(result["freshness"], "Fresh")
        self.assertTrue(any("fresh" in exp.lower() for exp in result["priority_explanations"]))

    def test_aging_report(self):
        """Report between 24h and 72h is Aging and receives -10 priority penalty."""
        report = Report(
            id=101,
            report_id="RPT-001",
            category="Roads",
            issue_type="Pothole",
            description="Aging report from 2 days ago",
            latitude=11.0168,
            longitude=76.9558,
            reported_time=self.ref_time - timedelta(hours=48),
            citizen_severity="High",
        )
        engine = VerificationEngine(
            incident=self.incident,
            reports=[report],
            reference_time=self.ref_time,
        )
        result = engine.evaluate_incident()

        self.assertEqual(result["freshness"], "Aging")
        # High severity (50) + conf_adj (2) - aging penalty (10) = 42
        self.assertEqual(result["priority_score"], 42)
        self.assertTrue(any("aging" in exp.lower() for exp in result["priority_explanations"]))

    def test_stale_report(self):
        """Report > 72 hours is Stale and receives -30 priority penalty."""
        report = Report(
            id=101,
            report_id="RPT-001",
            category="Roads",
            issue_type="Pothole",
            description="Stale report from 5 days ago",
            latitude=11.0168,
            longitude=76.9558,
            reported_time=self.ref_time - timedelta(hours=120),
            citizen_severity="High",
        )
        engine = VerificationEngine(
            incident=self.incident,
            reports=[report],
            reference_time=self.ref_time,
        )
        result = engine.evaluate_incident()

        self.assertEqual(result["freshness"], "Stale")
        # High severity (50) + conf_adj (2) - stale penalty (30) = 22
        self.assertEqual(result["priority_score"], 22)
        self.assertEqual(result["priority_level"], "Low")
        self.assertTrue(any("stale" in exp.lower() for exp in result["priority_explanations"]))

    def test_responder_verified(self):
        """Official responder verification sets score to 100 and status to Verified without penalty reduction."""
        # Report has missing location and conflicting evidence
        report = Report(
            id=101,
            report_id="RPT-001",
            category="Roads",
            issue_type="Pothole",
            description="Report with conflict and missing coordinates",
            latitude=None,
            longitude=None,
            reported_time=self.ref_time - timedelta(hours=1),
            citizen_severity="Critical",
            conflicting_evidence="Yes",
        )
        verification = ResponderVerification(
            id=1,
            incident_id=1,
            responder_id=99,
            verification_status="Verified",
            notes="Issue inspected and confirmed on site.",
        )
        engine = VerificationEngine(
            incident=self.incident,
            reports=[report],
            verifications=[verification],
            reference_time=self.ref_time,
        )
        result = engine.evaluate_incident()

        # Score must remain 100, status must be Verified
        self.assertEqual(result["confidence_score"], 100)
        self.assertEqual(result["status"], "Verified")
        # Conflict notice is preserved in explanation rather than dropping score
        self.assertTrue(any("conflict notice" in exp.lower() for exp in result["confidence_explanations"]))

    def test_responder_rejected(self):
        """Official responder rejection sets score to 0 and status to Rejected."""
        report = Report(
            id=101,
            report_id="RPT-001",
            category="Roads",
            issue_type="Pothole",
            description="False report",
            latitude=11.0168,
            longitude=76.9558,
            reported_time=self.ref_time - timedelta(hours=1),
            citizen_severity="Low",
        )
        verification = ResponderVerification(
            id=1,
            incident_id=1,
            responder_id=99,
            verification_status="Rejected",
            notes="No pothole found at specified location.",
        )
        engine = VerificationEngine(
            incident=self.incident,
            reports=[report],
            verifications=[verification],
            reference_time=self.ref_time,
        )
        result = engine.evaluate_incident()

        self.assertEqual(result["confidence_score"], 0)
        self.assertEqual(result["status"], "Rejected")

    def test_high_confidence_without_responder_verification(self):
        """High confidence score without official responder must be Corroborated, NOT Verified."""
        # 4 independent reports: base 10 + (3 * 20 = 60) = 70
        # + External Evidence: +15, High Quality: +15 -> Total 100
        reports = [
            Report(
                id=101 + i,
                report_id=f"RPT-00{i+1}",
                category="Roads",
                issue_type="Pothole",
                description=f"Independent report {i+1}",
                latitude=11.0168 + (i * 0.001),
                longitude=76.9558,
                reported_time=self.ref_time - timedelta(minutes=30 - (i * 5)),
                citizen_severity="Critical",
            )
            for i in range(4)
        ]
        evidence = [
            ExternalEvidence(
                id=1,
                incident_id=1,
                source_type="CCTV",
                source_status="High Quality",
            )
        ]
        engine = VerificationEngine(
            incident=self.incident,
            reports=reports,
            evidence=evidence,
            reference_time=self.ref_time,
        )
        result = engine.evaluate_incident()

        # Score is high (100)
        self.assertEqual(result["confidence_score"], 100)
        self.assertEqual(result["confidence_level"], "High")
        # Verification status MUST be Corroborated, NOT Verified!
        self.assertEqual(result["status"], "Corroborated")
        self.assertNotEqual(result["status"], "Verified")


if __name__ == "__main__":
    unittest.main()
