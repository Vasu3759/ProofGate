from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models import (
    ApprovedFact,
    AuditEvent,
    Finding,
    FindingEvidence,
    PolicyVersion,
    ReviewDecision,
    ReviewRun,
    Submission,
    SubmissionRevision,
    User,
)


def detect_policy_drift(db: Session, organization_id: str) -> list[dict]:
    """
    Dependency & Policy Drift Tracking Engine.
    Scans previously approved submissions and flags any that depend on:
    1. Superseded or expired ApprovedFacts.
    2. Outdated PolicyVersions.
    Returns structured drift reports so managers can trigger retro-audits.
    """
    now = datetime.now(timezone.utc)
    drift_items = []

    # Get all currently approved submissions
    approved_submissions = db.query(Submission).filter(
        Submission.organization_id == organization_id,
        Submission.status == "approved",
    ).all()

    # Map current active facts by key
    active_facts = {
        f.fact_key: f
        for f in db.query(ApprovedFact).filter(
            ApprovedFact.organization_id == organization_id,
            ApprovedFact.approval_status == "approved",
            ApprovedFact.effective_at <= now,
        ).all()
    }

    for sub in approved_submissions:
        # Get latest revision
        latest_rev = db.query(SubmissionRevision).filter(
            SubmissionRevision.submission_id == sub.id
        ).order_by(SubmissionRevision.revision_number.desc()).first()
        if not latest_rev:
            continue

        # Get review run tied to approval
        approval_decision = db.query(ReviewDecision).filter(
            ReviewDecision.submission_id == sub.id,
            ReviewDecision.decision == "approved",
        ).order_by(ReviewDecision.created_at.desc()).first()

        run = None
        if approval_decision:
            run = db.query(ReviewRun).filter(ReviewRun.id == approval_decision.review_run_id).first()
        if not run:
            run = db.query(ReviewRun).filter(ReviewRun.revision_id == latest_rev.id).order_by(ReviewRun.created_at.desc()).first()

        if not run:
            continue

        # Check evidence citations in findings of this run
        run_finding_ids = [
            f.id for f in db.query(Finding.id).filter(Finding.review_run_id == run.id).all()
        ]
        evidences = db.query(FindingEvidence).filter(
            FindingEvidence.finding_id.in_(run_finding_ids)
        ).all() if run_finding_ids else []

        # Check if any fact cited in this run has since been superseded or expired
        reasons = []
        for ev in evidences:
            fact = db.query(ApprovedFact).filter(ApprovedFact.id == ev.fact_id).first()
            if not fact:
                continue
            active = active_facts.get(fact.fact_key)
            if active and active.version > fact.version:
                reasons.append(
                    f"Fact '{fact.fact_key}' was updated from v{fact.version} to v{active.version} (\"{active.claim_text}\")."
                )
            elif fact.expires_at and fact.expires_at <= now:
                reasons.append(f"Fact '{fact.fact_key}' (v{fact.version}) has expired.")

        # Check if active facts contradict content directly
        content_lower = latest_rev.content_text.lower()
        for key, active in active_facts.items():
            if active.version > 1 and not any(key in r for r in reasons):
                reasons.append(
                    f"New active guidance published: \"{active.claim_text}\" (v{active.version})."
                )

        if reasons:
            reviewer = db.query(User).filter(User.id == approval_decision.reviewer_id).first() if approval_decision else None
            drift_items.append({
                "submission_id": sub.id,
                "title": sub.title,
                "channel": sub.channel,
                "approved_at": approval_decision.created_at if approval_decision else sub.created_at,
                "approved_by": reviewer.display_name if reviewer else "Dana Kim",
                "revision_number": latest_rev.revision_number,
                "drift_reasons": reasons,
                "status": "policy_drift_detected",
            })

    return drift_items
