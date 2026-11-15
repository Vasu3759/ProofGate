from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models import (
    ApprovedFact,
    AuditEvent,
    Finding,
    FindingEvidence,
    FindingPolicy,
    PolicyVersion,
    ReviewDecision,
    ReviewRun,
    ReviewRunPolicy,
    Submission,
    SubmissionRevision,
    User,
)


def detect_policy_drift(db: Session, organization_id: str) -> list[dict]:
    """
    Dependency & Policy Drift Tracking Engine.
    Scans previously approved submissions and flags ONLY approved content that
    actually depends on a changed or expired fact or an updated policy version.
    """
    now = datetime.now(timezone.utc)
    drift_items = []

    # Get all currently approved submissions
    approved_submissions = db.query(Submission).filter(
        Submission.organization_id == organization_id,
        Submission.status == "approved",
    ).all()

    # Map current active approved facts by key
    active_facts = {
        f.fact_key: f
        for f in db.query(ApprovedFact).filter(
            ApprovedFact.organization_id == organization_id,
            ApprovedFact.approval_status == "approved",
            ApprovedFact.effective_at <= now,
        ).all()
    }

    # Map current active policies by policy_id
    active_policies = {
        p.policy_id: p
        for p in db.query(PolicyVersion).filter(
            PolicyVersion.organization_id == organization_id,
            PolicyVersion.approval_status == "approved",
            PolicyVersion.effective_at <= now,
        ).all()
    }

    for sub in approved_submissions:
        latest_rev = db.query(SubmissionRevision).filter(
            SubmissionRevision.submission_id == sub.id
        ).order_by(SubmissionRevision.revision_number.desc()).first()
        if not latest_rev:
            continue

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

        # 1. Fact-level drift: Check ONLY facts that were actually cited in findings of this review run
        run_findings = db.query(Finding).filter(Finding.review_run_id == run.id).all()
        run_finding_ids = [f.id for f in run_findings]

        evidences = db.query(FindingEvidence).filter(
            FindingEvidence.finding_id.in_(run_finding_ids)
        ).all() if run_finding_ids else []

        reasons = []
        checked_facts = set()
        for ev in evidences:
            if ev.fact_id in checked_facts:
                continue
            checked_facts.add(ev.fact_id)

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

        # 2. Policy-version drift: Check if policies pinned to the review run have newer approved versions
        run_policies = db.query(ReviewRunPolicy).filter(ReviewRunPolicy.review_run_id == run.id).all()
        checked_policies = set()
        for rp in run_policies:
            pv = db.query(PolicyVersion).filter(PolicyVersion.id == rp.policy_version_id).first()
            if not pv or pv.policy_id in checked_policies:
                continue
            checked_policies.add(pv.policy_id)

            active_p = active_policies.get(pv.policy_id)
            if active_p and active_p.version > pv.version:
                reasons.append(
                    f"Brand policy '{active_p.policy.name if active_p.policy else pv.policy_id}' was updated from v{pv.version} to v{active_p.version}."
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
