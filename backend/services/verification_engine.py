from datetime import datetime, timedelta
from math import atan2, cos, radians, sin, sqrt
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.models import (
    EvaluationLabel,
    ExternalEvidence,
    Incident,
    Report,
    ResponderVerification,
)

EARTH_RADIUS_METERS = 6_371_000


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two coordinates in meters."""
    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(max(0.0, 1 - a)))
    return EARTH_RADIUS_METERS * c


class VerificationEngine:
    """
    Rule-based verification engine that calculates Confidence, Priority,
    Freshness, and Verification Status with full explainability.
    """

    BASE_SEVERITY_SCORES = {
        'Critical': 70,
        'High': 50,
        'Medium': 30,
        'Low': 10,
    }

    DUPLICATE_DISTANCE_THRESHOLD_METERS = 25.0
    DUPLICATE_TIME_THRESHOLD_MINUTES = 10.0

    def __init__(
        self,
        db: Optional[Session] = None,
        incident: Optional[Incident] = None,
        reports: Optional[List[Report]] = None,
        evidence: Optional[List[ExternalEvidence]] = None,
        verifications: Optional[List[ResponderVerification]] = None,
        reference_time: Optional[datetime] = None,
    ):
        self.db = db
        self.incident = incident
        self.reports = reports or []
        self.reference_time = reference_time or datetime.utcnow()

        if db is not None and incident is not None and getattr(incident, 'id', None) is not None:
            self.evidence = (
                db.execute(
                    select(ExternalEvidence).where(ExternalEvidence.incident_id == incident.id)
                ).scalars().all()
                if evidence is None
                else evidence
            )
            self.verifications = (
                db.execute(
                    select(ResponderVerification).where(ResponderVerification.incident_id == incident.id)
                ).scalars().all()
                if verifications is None
                else verifications
            )
        else:
            self.evidence = evidence or []
            self.verifications = verifications or []

    def get_reference_now(self) -> datetime:
        return self.reference_time

    def determine_freshness(self) -> str:
        """
        Determines freshness based on the most recent report relative to reference time.
        - Fresh: <= 24 hours
        - Aging: > 24 hours and <= 72 hours
        - Stale: > 72 hours
        """
        if not self.reports:
            return "Unknown"

        valid_times = [r.reported_time for r in self.reports if r.reported_time]
        if not valid_times:
            return "Unknown"

        most_recent_time = max(valid_times)
        age = self.get_reference_now() - most_recent_time

        if age <= timedelta(hours=24):
            return "Fresh"
        elif age <= timedelta(hours=72):
            return "Aging"
        else:
            return "Stale"

    def has_conflicting_evidence(self) -> bool:
        """Check if any report contains conflicting evidence indicators."""
        for r in self.reports:
            if r.conflicting_evidence:
                val = str(r.conflicting_evidence).strip().lower()
                if val in ['yes', 'true', 'conflicted', '1']:
                    return True
        return False

    def is_duplicate_pair(self, r1: Report, r2: Report) -> bool:
        """
        Determines if r2 is an obvious duplicate of r1 based on category,
        issue type, nearby location (<= 25m), and close timestamp (<= 10 mins).
        """
        if r1.category != r2.category or r1.issue_type != r2.issue_type:
            return False

        # Time check
        if r1.reported_time and r2.reported_time:
            time_diff_min = abs((r1.reported_time - r2.reported_time).total_seconds()) / 60.0
            if time_diff_min > self.DUPLICATE_TIME_THRESHOLD_MINUTES:
                return False
        elif r1.reported_time != r2.reported_time:
            return False

        # Location check
        if (
            r1.latitude is not None
            and r1.longitude is not None
            and r2.latitude is not None
            and r2.longitude is not None
        ):
            dist = haversine_distance_meters(r1.latitude, r1.longitude, r2.latitude, r2.longitude)
            return dist <= self.DUPLICATE_DISTANCE_THRESHOLD_METERS

        # If both are missing location and close in time with identical description
        if (
            r1.latitude is None
            and r2.latitude is None
            and r1.longitude is None
            and r2.longitude is None
        ):
            desc1 = (r1.description or "").strip().lower()
            desc2 = (r2.description or "").strip().lower()
            if desc1 and desc2 and desc1 == desc2:
                return True

        return False

    def cluster_independent_reports(self) -> Tuple[List[Report], List[Report]]:
        """
        Separates reports into independent unique reports and duplicate reports.
        """
        if not self.reports:
            return [], []

        # Sort deterministically by reported_time or id
        sorted_reports = sorted(
            self.reports,
            key=lambda r: (
                r.reported_time or datetime.min,
                str(getattr(r, 'report_id', '')) or str(getattr(r, 'id', ''))
            ),
        )

        unique_clusters: List[Report] = []
        duplicates: List[Report] = []

        for report in sorted_reports:
            is_dup = False
            for cluster_rep in unique_clusters:
                if self.is_duplicate_pair(cluster_rep, report):
                    is_dup = True
                    break
            if is_dup:
                duplicates.append(report)
            else:
                unique_clusters.append(report)

        return unique_clusters, duplicates

    def calculate_confidence(self) -> Dict[str, Any]:
        """
        Calculates confidence score (0-100) and human-readable explanations.
        Confidence represents how trustworthy and corroborated the incident information is.
        """
        explanations: List[str] = []

        responder_verified_true = any(v.verification_status == 'Verified' for v in self.verifications)
        responder_verified_false = any(v.verification_status == 'Rejected' for v in self.verifications)
        has_conflicts = self.has_conflicting_evidence()
        missing_location = any(r.latitude is None or r.longitude is None for r in self.reports)

        # 1. Official Responder Verification
        if responder_verified_true:
            score = 100
            explanations.append("Official Responder Verification: Score confirmed at 100 (On-site verified).")
            if has_conflicts:
                explanations.append("Conflict Notice: Prior conflicting citizen reports detected but resolved by official responder verification.")
            if missing_location:
                explanations.append("Location Notice: Missing citizen coordinates detected, but verified on-site by responder.")
            return {"score": score, "level": "High", "explanations": explanations}

        if responder_verified_false:
            score = 0
            explanations.append("Official Responder Verification: Score set to 0 (Rejected/False report).")
            if has_conflicts:
                explanations.append("Conflict Notice: Incident was officially rejected.")
            return {"score": score, "level": "Low", "explanations": explanations}

        # 2. Base score for citizen report
        score = 10
        explanations.append("Base score: +10 for initial citizen report.")

        # 3. Independent Corroboration
        unique_reports, duplicates = self.cluster_independent_reports()
        if duplicates:
            explanations.append(f"Deduplication: {len(duplicates)} duplicate/near-duplicate report(s) filtered out.")

        independent_count = len(unique_reports)
        corroborating_count = max(0, independent_count - 1)
        corroboration_points = min(60, corroborating_count * 20)

        if corroborating_count > 0:
            score += corroboration_points
            explanations.append(
                f"Corroboration: +{corroboration_points} from {corroborating_count} independent citizen report(s)."
            )
        else:
            explanations.append("Corroboration: +0 (Single uncorroborated report).")

        # 4. External Evidence
        if self.evidence:
            score += 15
            explanations.append("External Evidence: +15 for attached sensor/photo/CCTV evidence.")
            high_quality = any(e.source_status in ['High Quality', 'Verified'] for e in self.evidence)
            if high_quality:
                score += 15
                explanations.append("Evidence Quality: +15 for high-quality verified data source.")

        # 5. Penalties for non-responder verified incidents
        if missing_location:
            score -= 30
            explanations.append("Location Penalty: -30 due to missing precise coordinates.")

        if has_conflicts:
            score -= 40
            explanations.append("Conflict Penalty: -40 due to conflicting reports/evidence.")

        score = max(0, min(100, score))

        if score >= 70:
            level = "High"
        elif score >= 40:
            level = "Medium"
        else:
            level = "Low"

        return {"score": score, "level": level, "explanations": explanations}

    def calculate_priority(self, confidence_score: int, freshness: str) -> Dict[str, Any]:
        """
        Calculates priority score (0-100) and human-readable explanations.
        Priority represents how urgently municipal authorities should act.
        """
        explanations: List[str] = []

        # Determine highest severity among reports
        highest_severity = "Low"
        severity_levels = ["Low", "Medium", "High", "Critical"]
        for r in self.reports:
            if r.citizen_severity in severity_levels:
                if severity_levels.index(r.citizen_severity) > severity_levels.index(highest_severity):
                    highest_severity = r.citizen_severity

        base_priority = self.BASE_SEVERITY_SCORES.get(highest_severity, 10)
        score = base_priority
        explanations.append(f"Base Severity ({highest_severity}): +{base_priority}.")

        # Impact (Independent Corroborating Reports)
        unique_reports, _ = self.cluster_independent_reports()
        corroborating_count = max(0, len(unique_reports) - 1)
        impact_points = min(20, corroborating_count * 5)
        if impact_points > 0:
            score += impact_points
            explanations.append(f"Impact: +{impact_points} from {corroborating_count} corroborating report(s).")

        # Confidence Adjustment (weighted 20%)
        conf_adj = int(confidence_score * 0.2)
        score += conf_adj
        explanations.append(f"Confidence Adjustment: +{conf_adj} (weighted by {confidence_score}% confidence).")

        # Freshness Adjustment
        if freshness == "Fresh":
            explanations.append("Freshness: +0 (information is fresh, <=24h).")
        elif freshness == "Aging":
            score -= 10
            explanations.append("Freshness Penalty: -10 (information is aging, 24h-72h).")
        elif freshness == "Stale":
            score -= 30
            explanations.append("Freshness Penalty: -30 (information is stale, >72h).")
        else:
            explanations.append("Freshness: Unknown freshness status.")

        score = max(0, min(100, score))

        if score >= 80:
            level = "Critical"
        elif score >= 60:
            level = "High"
        elif score >= 30:
            level = "Medium"
        else:
            level = "Low"

        return {"score": score, "level": level, "explanations": explanations}

    def determine_verification_status(self, confidence_score: int, freshness: str) -> str:
        """
        Determines the Verification Status:
        - Verified: Official responder marked as Verified
        - Rejected: Official responder marked as Rejected
        - Conflicted: Conflicting reports/evidence present
        - Corroborated: High confidence (>=70) without official responder verification
        - Pending: Insufficient evidence to corroborate or awaiting responder
        - Unknown: Critical information missing (no reports or missing location on unverified report)
        """
        responder_verified_true = any(v.verification_status == 'Verified' for v in self.verifications)
        responder_verified_false = any(v.verification_status == 'Rejected' for v in self.verifications)

        if responder_verified_true:
            return "Verified"
        if responder_verified_false:
            return "Rejected"

        if self.has_conflicting_evidence():
            return "Conflicted"

        if not self.reports:
            return "Unknown"

        # Missing critical information check
        all_missing_loc = all(r.latitude is None or r.longitude is None for r in self.reports)
        if all_missing_loc and not self.evidence:
            return "Unknown"

        # High confidence without responder verification
        if confidence_score >= 70:
            return "Corroborated"

        return "Pending"

    def evaluate_incident(self) -> Dict[str, Any]:
        freshness = self.determine_freshness()
        conf_result = self.calculate_confidence()
        prio_result = self.calculate_priority(conf_result["score"], freshness)
        status = self.determine_verification_status(conf_result["score"], freshness)
        recommended_action = generate_recommended_action(status, prio_result["level"], freshness)

        return {
            "confidence_score": conf_result["score"],
            "confidence_level": conf_result["level"],
            "confidence_explanations": conf_result["explanations"],
            "priority_score": prio_result["score"],
            "priority_level": prio_result["level"],
            "priority_explanations": prio_result["explanations"],
            "freshness": freshness,
            "status": status,
            "recommended_action": recommended_action,
        }

    def evaluate_full_summary(self) -> Dict[str, Any]:
        evaluation = self.evaluate_incident()
        unique_reports, duplicates = self.cluster_independent_reports()

        valid_times = [r.reported_time for r in self.reports if r.reported_time]
        last_reported_time = max(valid_times) if valid_times else (self.incident.created_at if self.incident else None)

        valid_coords = [(r.latitude, r.longitude) for r in self.reports if r.latitude is not None and r.longitude is not None]
        lat = valid_coords[0][0] if valid_coords else None
        lon = valid_coords[0][1] if valid_coords else None

        return {
            "incident_id": self.incident.incident_id if self.incident else "",
            "category": self.incident.category if self.incident else (self.reports[0].category if self.reports else None),
            "issue_type": self.incident.issue_type if self.incident else (self.reports[0].issue_type if self.reports else None),
            "zone": self.incident.zone if self.incident else (self.reports[0].zone if self.reports else None),
            "status": evaluation["status"],
            "human_status": self.incident.human_status if self.incident else "Awaiting Review",
            "priority_score": evaluation["priority_score"],
            "priority_level": evaluation["priority_level"],
            "confidence_score": evaluation["confidence_score"],
            "confidence_level": evaluation["confidence_level"],
            "freshness": evaluation["freshness"],
            "total_reports_count": len(self.reports),
            "independent_reports_count": len(unique_reports),
            "duplicate_reports_count": len(duplicates),
            "latitude": lat,
            "longitude": lon,
            "last_reported_time": last_reported_time,
            "created_at": self.incident.created_at if self.incident else datetime.utcnow(),
            "updated_at": self.incident.updated_at if self.incident else datetime.utcnow(),
            "confidence_explanations": evaluation["confidence_explanations"],
            "priority_explanations": evaluation["priority_explanations"],
            "recommended_action": evaluation["recommended_action"],
        }

    def update_evaluation_labels(self) -> Dict[str, Any]:
        evaluation = self.evaluate_incident()
        unique_reports, duplicates = self.cluster_independent_reports()

        valid_times = [r.reported_time for r in self.reports if r.reported_time]
        last_reported_time = max(valid_times) if valid_times else (self.incident.created_at if self.incident else None)

        valid_coords = [(r.latitude, r.longitude) for r in self.reports if r.latitude is not None and r.longitude is not None]
        lat = valid_coords[0][0] if valid_coords else None
        lon = valid_coords[0][1] if valid_coords else None

        if self.db is not None:
            for report in self.reports:
                label = self.db.execute(
                    select(EvaluationLabel).where(EvaluationLabel.report_id == report.id)
                ).scalar_one_or_none()
                if not label:
                    label = EvaluationLabel(report_id=report.id)
                    self.db.add(label)

                label.simulated_confidence_score = float(evaluation["confidence_score"])
                label.simulated_verification_state = evaluation["status"]
                label.simulated_priority_score = float(evaluation["priority_score"])
                label.simulated_priority = evaluation["priority_level"]

                report.freshness_status = evaluation["freshness"]
                report.location_status = (
                    "Available" if report.latitude is not None and report.longitude is not None else "Missing"
                )

            if self.incident is not None:
                self.incident.status = evaluation["status"]
                self.incident.priority_score = int(evaluation["priority_score"])
                self.incident.priority_level = evaluation["priority_level"]
                self.incident.confidence_score = int(evaluation["confidence_score"])
                self.incident.confidence_level = evaluation["confidence_level"]
                self.incident.freshness_status = evaluation["freshness"]
                self.incident.total_reports_count = len(self.reports)
                self.incident.independent_reports_count = len(unique_reports)
                self.incident.duplicate_reports_count = len(duplicates)
                self.incident.latitude = lat
                self.incident.longitude = lon
                self.incident.last_reported_time = last_reported_time
            self.db.flush()

        return evaluation



def generate_recommended_action(status: str, priority_level: str, freshness: str) -> str:
    """Generates an explainable decision-support recommendation for municipal officers."""
    if status == "Verified":
        if priority_level in ["Critical", "High"]:
            return "Recommend immediate response/dispatch."
        return "Verified incident; assign to departmental maintenance schedule."
    elif status == "Rejected":
        return "No action required; incident rejected by official responder."
    elif status == "Conflicted":
        return "Manual verification required due to conflicting reports."
    elif freshness == "Stale":
        return "Recommend re-verification because information is stale."
    elif status == "Corroborated":
        if priority_level in ["Critical", "High"]:
            return "Recommend field verification."
        return "Corroborated by crowd; schedule routine field verification."
    elif status == "Unknown":
        return "Request additional citizen details or precise location coordinates."
    else:  # Pending
        if priority_level in ["Critical", "High"]:
            return "High priority pending corroboration; monitor closely or dispatch probe."
        return "Insufficient corroboration; monitor or verify."

