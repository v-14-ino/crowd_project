import csv
import logging
import sys
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy.exc import SQLAlchemyError

from database.connection import SessionLocal
from models.models import (
    EvaluationLabel,
    ExternalEvidence,
    Incident,
    IncidentReport,
    Report,
    ResponderVerification,
)

DATA_FILE = Path(__file__).resolve().parents[1].parent / "dataset" / "municipality_crowd_reports_10000.csv"
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("import_dataset")

VALID_SOURCE_STATUSES = {"Supports", "Neutral", "Contradicts", "Not Available", "Unavailable"}
VALID_VERIFICATION_STATUSES = {"Confirmed", "Rejected", "Pending", "Unable to Verify"}


def parse_float(value):
    if value is None or value.strip() == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_int(value):
    if value is None or value.strip() == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def parse_bool(value):
    if value is None:
        return None
    value_lower = value.strip().lower()
    if value_lower in {"true", "1", "yes"}:
        return True
    if value_lower in {"false", "0", "no"}:
        return False
    return None


def parse_datetime(value):
    if value is None or value.strip() == "":
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None


def import_dataset():
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_FILE}")

    rows_processed = 0
    successful = 0
    skipped = 0
    failed = 0

    session = SessionLocal()
    try:
        with DATA_FILE.open(newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                rows_processed += 1
                try:
                    report_id = row.get("report_id", "").strip()
                    incident_id = row.get("incident_id", "").strip()

                    if not report_id or not incident_id:
                        logger.warning("Skipping row %s: missing report_id or incident_id", rows_processed)
                        skipped += 1
                        continue

                    existing_report = session.query(Report).filter_by(report_id=report_id).one_or_none()
                    if existing_report is not None:
                        skipped += 1
                        continue

                    incident = session.query(Incident).filter_by(incident_id=incident_id).one_or_none()
                    if incident is None:
                        incident = Incident(
                            incident_id=incident_id,
                            category=row.get("category", None) or None,
                            issue_type=row.get("issue_type", None) or None,
                            zone=row.get("zone", None) or None,
                            status="Open",
                        )
                        session.add(incident)
                        session.flush()

                    report = Report(
                        report_id=report_id,
                        category=row.get("category", None) or None,
                        issue_type=row.get("issue_type", None) or None,
                        description=row.get("description", None) or None,
                        zone=row.get("zone", None) or None,
                        latitude=parse_float(row.get("latitude")),
                        longitude=parse_float(row.get("longitude")),
                        reported_time=parse_datetime(row.get("reported_time")),
                        citizen_severity=row.get("citizen_severity", None) or None,
                        corroborating_reports=parse_int(row.get("corroborating_reports")),
                        location_status=row.get("location_status", None) or None,
                        freshness_status=row.get("freshness_status", None) or None,
                        conflicting_evidence=row.get("conflicting_evidence", None) or None,
                    )
                    session.add(report)
                    session.flush()

                    incident_report = IncidentReport(incident_id=incident.id, report_id=report.id)
                    session.add(incident_report)

                    source_status = row.get("external_source_status", None)
                    if source_status:
                        source_status = source_status.strip()
                        if source_status not in VALID_SOURCE_STATUSES:
                            source_status = "Not Available"
                        evidence = ExternalEvidence(
                            incident_id=incident.id,
                            source_type="Synthetic Dataset",
                            source_status=source_status,
                            observed_at=parse_datetime(row.get("reported_time")),
                            freshness_status=row.get("freshness_status", None) or None,
                            details=row.get("description", None) or None,
                        )
                        session.add(evidence)

                    verification_status = row.get("responder_verification", None)
                    if verification_status:
                        verification_status = verification_status.strip()
                        if verification_status not in VALID_VERIFICATION_STATUSES:
                            verification_status = "Pending"
                        verification = ResponderVerification(
                            incident_id=incident.id,
                            responder_id=None,
                            verification_status=verification_status,
                            notes="Imported from synthetic dataset",
                            verified_at=parse_datetime(row.get("reported_time")),
                        )
                        session.add(verification)

                    evaluation = EvaluationLabel(
                        report_id=report.id,
                        ground_truth_verified=parse_bool(row.get("ground_truth_verified")),
                        simulated_confidence_score=parse_float(row.get("confidence_score")),
                        simulated_verification_state=row.get("verification_state", None) or None,
                        simulated_priority_score=parse_float(row.get("priority_score")),
                        simulated_priority=row.get("priority", None) or None,
                    )
                    session.add(evaluation)

                    successful += 1
                    if rows_processed % 500 == 0:
                        session.commit()
                except Exception as row_error:
                    session.rollback()
                    failed += 1
                    logger.warning("Row %s failed and was skipped: %s", rows_processed, row_error)
                    continue
            session.commit()
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        failed += 1
    finally:
        session.close()

    logger.info("\nDataset Import Complete")
    logger.info("Rows processed: %s", rows_processed)
    logger.info("Successfully imported: %s", successful)
    logger.info("Skipped: %s", skipped)
    logger.info("Failed: %s", failed)

    session = SessionLocal()
    try:
        report_count = session.query(Report).count()
        incident_count = session.query(Incident).count()
        logger.info("Reports in database: %s", report_count)
        logger.info("Unique incidents: %s", incident_count)
    finally:
        session.close()


if __name__ == "__main__":
    import_dataset()
