from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from database.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=True)
    role = Column(String(50), nullable=False, default="citizen")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(String(64), nullable=False, unique=True, index=True)
    category = Column(String(80), nullable=True, index=True)
    issue_type = Column(String(120), nullable=True)
    zone = Column(String(80), nullable=True, index=True)
    status = Column(String(80), nullable=False, default="Pending", index=True)
    human_status = Column(String(80), nullable=False, default="Awaiting Review", index=True)
    priority_score = Column(Integer, nullable=False, default=0, index=True)
    priority_level = Column(String(50), nullable=False, default="Low", index=True)
    confidence_score = Column(Integer, nullable=False, default=0, index=True)
    confidence_level = Column(String(50), nullable=False, default="Low", index=True)
    freshness_status = Column(String(50), nullable=False, default="Fresh", index=True)
    total_reports_count = Column(Integer, nullable=False, default=1)
    independent_reports_count = Column(Integer, nullable=False, default=1)
    duplicate_reports_count = Column(Integer, nullable=False, default=0)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    last_reported_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    incident_reports = relationship("IncidentReport", back_populates="incident", cascade="all, delete-orphan")
    external_evidence = relationship("ExternalEvidence", back_populates="incident", cascade="all, delete-orphan")
    responder_verifications = relationship("ResponderVerification", back_populates="incident", cascade="all, delete-orphan")



class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String(64), nullable=False, unique=True, index=True)
    category = Column(String(80), nullable=True, index=True)
    issue_type = Column(String(120), nullable=True)
    description = Column(Text, nullable=True)
    zone = Column(String(80), nullable=True, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    reported_time = Column(DateTime, nullable=True, index=True)
    citizen_severity = Column(String(50), nullable=True)
    corroborating_reports = Column(Integer, nullable=True)
    location_status = Column(String(80), nullable=True)
    freshness_status = Column(String(80), nullable=True)
    conflicting_evidence = Column(String(80), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    incident_reports = relationship("IncidentReport", back_populates="report", cascade="all, delete-orphan")
    evaluation_label = relationship("EvaluationLabel", back_populates="report", uselist=False, cascade="all, delete-orphan")


class IncidentReport(Base):
    __tablename__ = "incident_reports"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    incident = relationship("Incident", back_populates="incident_reports")
    report = relationship("Report", back_populates="incident_reports")


class ExternalEvidence(Base):
    __tablename__ = "external_evidence"

    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(String(64), nullable=True, unique=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="SET NULL"), nullable=True, index=True)
    source_type = Column(String(120), nullable=True)
    source_status = Column(String(80), nullable=True)
    observed_at = Column(DateTime, nullable=True)
    freshness_status = Column(String(80), nullable=True)
    details = Column(Text, nullable=True)
    filename = Column(String(255), nullable=True)
    file_path = Column(String(512), nullable=True)
    file_url = Column(String(512), nullable=True)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    incident = relationship("Incident", back_populates="external_evidence")
    report = relationship("Report")



class ResponderVerification(Base):
    __tablename__ = "responder_verifications"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    responder_id = Column(Integer, nullable=True)
    responder_name = Column(String(120), nullable=True)
    verification_status = Column(String(80), nullable=True)
    notes = Column(Text, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    incident = relationship("Incident", back_populates="responder_verifications")


class EvaluationLabel(Base):
    __tablename__ = "evaluation_labels"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    ground_truth_verified = Column(Boolean, nullable=True)
    simulated_confidence_score = Column(Float, nullable=True)
    simulated_verification_state = Column(String(120), nullable=True)
    simulated_priority_score = Column(Float, nullable=True)
    simulated_priority = Column(String(80), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    report = relationship("Report", back_populates="evaluation_label")
