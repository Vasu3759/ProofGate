from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models import (
    ApprovedFact,
    AuditEvent,
    Finding,
    FindingEvidence,
    PolicyVersion,
    ReReviewTask,
    ReviewDecision,
    ReviewRun,
    ReviewRunPolicy,
    Submission,
    SubmissionRevision,
    User,
)


def build_change_impact_graph(db: Session, organization_id: str) -> dict:
    """
    Change-Impact Re-review Graph:
    Maps approved facts and policy versions to the exact content revisions and human
    decisions that cited them. Shows which assets are affected and why.
    """
    now = datetime.now(timezone.utc)
    nodes = []
    edges = []

    # 1. Fact Nodes
    facts = db.query(ApprovedFact).filter(ApprovedFact.organization_id == organization_id).all()
    for f in facts:
        nodes.append({
            "id": f"fact-{f.id}",
            "type": "fact",
            "label": f"{f.label} (v{f.version})",
            "fact_key": f.fact_key,
            "version": f.version,
            "status": f.approval_status,
        })

    # 2. Policy Version Nodes
    policies = db.query(PolicyVersion).filter(PolicyVersion.organization_id == organization_id).all()
    for p in policies:
        nodes.append({
            "id": f"policy-{p.id}",
            "type": "policy",
            "label": f"Policy v{p.version} [{p.scope}]",
            "scope": p.scope,
            "precedence": p.precedence,
            "status": p.approval_status,
        })

    # 3. Submission & Revision Nodes with Impact Edges
    submissions = db.query(Submission).filter(Submission.organization_id == organization_id).all()
    for s in submissions:
        nodes.append({
            "id": f"sub-{s.id}",
            "type": "submission",
            "label": s.title,
            "channel": s.channel,
            "status": s.status,
        })

        # Find review runs and evidences
        runs = db.query(ReviewRun).filter(ReviewRun.submission_id == s.id).all()
        for r in runs:
            findings = db.query(Finding).filter(Finding.review_run_id == r.id).all()
            for f in findings:
                evidence = db.query(FindingEvidence).filter(FindingEvidence.finding_id == f.id).first()
                if evidence:
                    edges.append({
                        "source": f"fact-{evidence.fact_id}",
                        "target": f"sub-{s.id}",
                        "relationship": "cited_by",
                        "fact_version": evidence.fact_version,
                    })
            for rp in db.query(ReviewRunPolicy).filter(ReviewRunPolicy.review_run_id == r.id).all():
                edges.append({
                    "source": f"policy-{rp.policy_version_id}",
                    "target": f"sub-{s.id}",
                    "relationship": "governed_by",
                })

    return {"nodes": nodes, "edges": edges}


def generate_targeted_rereview_tasks(db: Session, organization_id: str) -> list[ReReviewTask]:
    """
    Automated Re-Review Task Generator:
    Detects affected content from changed/expired facts or updated policies
    and creates targeted re-review work items so teams recheck only impacted content.
    """
    now = datetime.now(timezone.utc)
    from app.domains.drift import detect_policy_drift

    drift_items = detect_policy_drift(db, organization_id)
    created_tasks = []

    for item in drift_items:
        sub_id = item["submission_id"]
        latest_rev = db.query(SubmissionRevision).filter(
            SubmissionRevision.submission_id == sub_id
        ).order_by(SubmissionRevision.revision_number.desc()).first()

        if not latest_rev:
            continue

        existing = db.query(ReReviewTask).filter(
            ReReviewTask.submission_id == sub_id,
            ReReviewTask.status.in_(["pending", "in_progress"]),
        ).first()

        if not existing:
            task = ReReviewTask(
                organization_id=organization_id,
                submission_id=sub_id,
                revision_id=latest_rev.id,
                trigger_type="fact_updated",
                trigger_source_id="drift-engine",
                impact_summary="; ".join(item["drift_reasons"]),
                status="pending",
            )
            db.add(task)
            created_tasks.append(task)

    if created_tasks:
        db.commit()

    return db.query(ReReviewTask).filter(
        ReReviewTask.organization_id == organization_id,
        ReReviewTask.status.in_(["pending", "in_progress"]),
    ).order_by(ReReviewTask.created_at.desc()).all()
