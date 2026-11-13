import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def now_utc():
    return datetime.now(timezone.utc)


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("organization_id", "user_id"), CheckConstraint("role in ('admin','brand_manager','reviewer','creator')"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class EvidenceSource(Base):
    __tablename__ = "evidence_sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_version: Mapped[str] = mapped_column(String(40), nullable=False)
    owner: Mapped[str] = mapped_column(String(160), nullable=False)
    approval_status: Mapped[str] = mapped_column(String(24), default="approved", nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class ApprovedFact(Base):
    __tablename__ = "approved_facts"
    __table_args__ = (UniqueConstraint("organization_id", "fact_key", "version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("evidence_sources.id", ondelete="RESTRICT"), index=True)
    fact_key: Mapped[str] = mapped_column(String(100), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str] = mapped_column(String(160), nullable=False)
    approval_status: Mapped[str] = mapped_column(String(24), default="approved", nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    source: Mapped[EvidenceSource] = relationship()


class BrandPolicy(Base):
    __tablename__ = "brand_policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="active", nullable=False)


class PolicyVersion(Base):
    __tablename__ = "policy_versions"
    __table_args__ = (UniqueConstraint("policy_id", "version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    policy_id: Mapped[str] = mapped_column(ForeignKey("brand_policies.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    rule_text: Mapped[str] = mapped_column(Text, nullable=False)
    approval_status: Mapped[str] = mapped_column(String(24), default="approved", nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class Submission(Base):
    __tablename__ = "submissions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    channel: Mapped[str] = mapped_column(String(100), default="Marketing", nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class SubmissionRevision(Base):
    __tablename__ = "submission_revisions"
    __table_args__ = (UniqueConstraint("submission_id", "revision_number"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"), index=True)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class ReviewRun(Base):
    __tablename__ = "review_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"), index=True)
    revision_id: Mapped[str] = mapped_column(ForeignKey("submission_revisions.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(24), default="completed", nullable=False)
    pipeline_version: Mapped[str] = mapped_column(String(40), default="deterministic-v1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class ReviewRunPolicy(Base):
    __tablename__ = "review_run_policy_versions"
    review_run_id: Mapped[str] = mapped_column(ForeignKey("review_runs.id", ondelete="CASCADE"), primary_key=True)
    policy_version_id: Mapped[str] = mapped_column(ForeignKey("policy_versions.id", ondelete="RESTRICT"), primary_key=True)


class Finding(Base):
    __tablename__ = "findings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    review_run_id: Mapped[str] = mapped_column(ForeignKey("review_runs.id", ondelete="CASCADE"), index=True)
    finding_type: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)


class FindingPolicy(Base):
    __tablename__ = "finding_policy_versions"
    finding_id: Mapped[str] = mapped_column(ForeignKey("findings.id", ondelete="CASCADE"), primary_key=True)
    policy_version_id: Mapped[str] = mapped_column(ForeignKey("policy_versions.id", ondelete="RESTRICT"), primary_key=True)


class FindingEvidence(Base):
    __tablename__ = "finding_evidence"
    finding_id: Mapped[str] = mapped_column(ForeignKey("findings.id", ondelete="CASCADE"), primary_key=True)
    fact_id: Mapped[str] = mapped_column(ForeignKey("approved_facts.id", ondelete="RESTRICT"), primary_key=True)
    fact_version: Mapped[int] = mapped_column(Integer, nullable=False)
    source_id: Mapped[str] = mapped_column(ForeignKey("evidence_sources.id", ondelete="RESTRICT"), nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)


class CorrectionSuggestion(Base):
    __tablename__ = "correction_suggestions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    finding_id: Mapped[str] = mapped_column(ForeignKey("findings.id", ondelete="CASCADE"), index=True)
    suggested_text: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)


class ReviewDecision(Base):
    __tablename__ = "review_decisions"
    __table_args__ = (CheckConstraint("decision in ('approved','rejected','needs_changes')"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"), index=True)
    revision_id: Mapped[str] = mapped_column(ForeignKey("submission_revisions.id", ondelete="RESTRICT"), nullable=False)
    review_run_id: Mapped[str] = mapped_column(ForeignKey("review_runs.id", ondelete="RESTRICT"), nullable=False)
    reviewer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    decision: Mapped[str] = mapped_column(String(24), nullable=False)
    comments: Mapped[str] = mapped_column(Text, default="", nullable=False)
    override_justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
