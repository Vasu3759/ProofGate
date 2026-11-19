from datetime import datetime, timedelta, timezone
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.domains.auth import Actor, create_access_token, get_current_actor, require_roles
from app.domains.documents import extract_text_from_file
from app.domains.drift import detect_policy_drift
from app.domains.impact_graph import build_change_impact_graph, generate_targeted_rereview_tasks
from app.domains.policy_intelligence import detect_and_index_policy_conflicts, resolve_policy_conflict
from app.domains.review import run_review
from app.models import (
    ApprovedFact, AuditEvent, BrandPolicy, CorrectionSuggestion, EvidenceSource,
    Finding, FindingEvidence, FindingPolicy, Membership, Organization, PolicyConflict,
    PolicyVersion, ReReviewTask, ReviewDecision, ReviewRun, ReviewRunPolicy, Submission,
    SubmissionRevision, User,
)
from app.schemas import DecisionCreate, FactCreate, LoginRequest, PolicyConflictResolve, RevisionCreate, SubmissionCreate

app = FastAPI(title="ProofGate API", version="0.3.0", description="Enterprise brand governance platform with change-impact intelligence.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def hash_content(content: str) -> str:
    import hashlib
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def get_submission(db: Session, actor: Actor, submission_id: str) -> Submission:
    submission = db.query(Submission).filter(
        Submission.id == submission_id,
        Submission.organization_id == actor.organization.id,
    ).first()
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found.")
    return submission


def latest_revision(db: Session, submission: Submission):
    return db.query(SubmissionRevision).filter(
        SubmissionRevision.submission_id == submission.id,
    ).order_by(SubmissionRevision.revision_number.desc()).first()


def pack_fact(fact: ApprovedFact):
    return {
        "id": fact.id, "fact_key": fact.fact_key, "version": fact.version,
        "label": fact.label, "claim_text": fact.claim_text, "owner": fact.owner,
        "approval_status": fact.approval_status, "source_name": fact.source.name,
        "source_version": fact.source.source_version, "effective_at": fact.effective_at,
    }


def pack_review(db: Session, run: ReviewRun):
    findings = db.query(Finding).filter(Finding.review_run_id == run.id).all()
    result = []
    for finding in findings:
        evidence = db.query(FindingEvidence).filter(FindingEvidence.finding_id == finding.id).first()
        citation = None
        if evidence:
            fact = db.query(ApprovedFact).filter(ApprovedFact.id == evidence.fact_id).first()
            source = db.query(EvidenceSource).filter(EvidenceSource.id == evidence.source_id).first()
            citation = {
                "fact_id": evidence.fact_id,
                "fact_version": evidence.fact_version,
                "fact_key": fact.fact_key if fact else None,
                "label": fact.label if fact else None,
                "source_name": source.name if source else None,
                "source_version": source.source_version if source else None,
                "excerpt": evidence.excerpt,
            }
        suggestion = db.query(CorrectionSuggestion).filter(CorrectionSuggestion.finding_id == finding.id).first()
        policy_link = db.query(FindingPolicy).filter(FindingPolicy.finding_id == finding.id).first()
        policy = db.query(PolicyVersion).filter(PolicyVersion.id == policy_link.policy_version_id).first() if policy_link else None
        policy_name = db.query(BrandPolicy).filter(BrandPolicy.id == policy.policy_id).first().name if policy else None
        result.append({
            "id": finding.id, "finding_type": finding.finding_type,
            "severity": finding.severity, "claim_text": finding.claim_text,
            "status": finding.status, "explanation": finding.explanation,
            "evidence": citation,
            "policy_citation": ({"name": policy_name, "version": policy.version, "rule_text": policy.rule_text} if policy else None),
            "suggestion": ({"id": suggestion.id, "text": suggestion.suggested_text, "rationale": suggestion.rationale} if suggestion else None),
        })
    policy_ids = [row.policy_version_id for row in db.query(ReviewRunPolicy).filter(ReviewRunPolicy.review_run_id == run.id).all()]
    policies = db.query(PolicyVersion).filter(PolicyVersion.id.in_(policy_ids)).all() if policy_ids else []
    audit = db.query(AuditEvent).filter(
        AuditEvent.action == "review.completed",
        AuditEvent.entity_id == run.submission_id,
        AuditEvent.metadata_json["review_run_id"].as_string() == run.id,
    ).order_by(AuditEvent.created_at.desc()).first()
    if not audit:
        # Fallback to matching revision_id if as_string filter syntax is engine-dependent
        audit = db.query(AuditEvent).filter(
            AuditEvent.action == "review.completed",
            AuditEvent.entity_id == run.submission_id,
        ).order_by(AuditEvent.created_at.desc()).first()
        if audit and audit.metadata_json.get("review_run_id") != run.id:
            audit = None
    metadata = audit.metadata_json if audit else {}

    return {
        "id": run.id, "revision_id": run.revision_id, "pipeline_version": run.pipeline_version,
        "created_at": run.created_at, "policies": [{"id": p.id, "version": p.version, "rule_text": p.rule_text} for p in policies],
        "findings": result,
        "ai_metadata": {
            "pipeline_engine": metadata.get("pipeline_engine", "deterministic-v1"),
            "tone_score": metadata.get("tone_score", 100),
            "detected_tone": metadata.get("detected_tone", "Neutral"),
            "tone_summary": metadata.get("tone_summary", ""),
        },
    }


@app.get("/health")
def health():
    return {"status": "ok", "demo_mode": settings.demo_mode, "version": "0.3.0"}


@app.post("/api/auth/token")
def login_for_access_token(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Production OIDC/JWT Authentication Token Exchange:
    Issues a cryptographically signed Bearer JWT carrying tenant boundaries and roles.
    """
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    org = db.query(Organization).filter(Organization.slug == payload.organization_slug).first()
    if not user or not org:
        raise HTTPException(status_code=401, detail="Invalid credentials or organization.")
    membership = db.query(Membership).filter(
        Membership.user_id == user.id,
        Membership.organization_id == org.id,
        Membership.active.is_(True),
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="User is not an active member of this organization.")

    token = create_access_token(user.id, user.email, org.slug, membership.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email, "name": user.display_name, "role": membership.role},
        "organization": {"id": org.id, "name": org.name, "slug": org.slug},
    }


@app.get("/api/me")
def me(actor: Actor = Depends(get_current_actor)):
    return {"id": actor.user.id, "name": actor.user.display_name, "email": actor.user.email, "role": actor.role, "organization": actor.organization.name, "organization_id": actor.organization.id, "demo_mode": settings.demo_mode}


@app.get("/api/dashboard")
def dashboard(actor: Actor = Depends(get_current_actor), db: Session = Depends(get_db)):
    submissions = db.query(Submission).filter(Submission.organization_id == actor.organization.id).all()
    decisions = db.query(ReviewDecision).filter(ReviewDecision.organization_id == actor.organization.id).all()
    open_reviews = sum(1 for item in submissions if item.status in {"in_review", "needs_changes"})
    reviews_completed = db.query(ReviewRun).filter(ReviewRun.organization_id == actor.organization.id, ReviewRun.status == "completed").count()
    ordered = db.query(Submission).filter(Submission.organization_id == actor.organization.id).order_by(Submission.created_at.desc()).limit(5).all()
    return {"reviews_completed": reviews_completed, "submissions": len(submissions), "pending_approvals": sum(1 for item in submissions if item.status == "in_review"), "needs_changes": sum(1 for item in submissions if item.status == "needs_changes"), "decisions": len(decisions), "recent": [{"id": item.id, "title": item.title, "status": item.status} for item in ordered], "open_reviews": open_reviews}


@app.get("/api/audit")
def audit_events(entity_id: str | None = None, actor: Actor = Depends(get_current_actor), db: Session = Depends(get_db)):
    query = db.query(AuditEvent).filter(AuditEvent.organization_id == actor.organization.id)
    if entity_id:
        query = query.filter(AuditEvent.entity_id == entity_id)
    rows = query.order_by(AuditEvent.created_at.desc()).limit(50).all()
    return [{"id": row.id, "action": row.action, "entity_type": row.entity_type, "entity_id": row.entity_id, "actor": db.query(User).filter(User.id == row.actor_id).first().display_name, "metadata": row.metadata_json, "created_at": row.created_at} for row in rows]


@app.get("/api/knowledge/facts")
def list_facts(actor: Actor = Depends(get_current_actor), db: Session = Depends(get_db)):
    facts = db.query(ApprovedFact).filter(ApprovedFact.organization_id == actor.organization.id).order_by(ApprovedFact.fact_key, ApprovedFact.version.desc()).all()
    return [pack_fact(fact) for fact in facts]


@app.get("/api/knowledge/summary")
def knowledge_summary(actor: Actor = Depends(get_current_actor), db: Session = Depends(get_db)):
    facts = db.query(ApprovedFact).filter(ApprovedFact.organization_id == actor.organization.id).all()
    sources = db.query(EvidenceSource).filter(EvidenceSource.organization_id == actor.organization.id).all()
    policies = db.query(PolicyVersion).filter(PolicyVersion.organization_id == actor.organization.id, PolicyVersion.approval_status == "approved").all()
    now = datetime.now(timezone.utc)
    expiring = sum(1 for fact in facts if fact.expires_at and fact.expires_at <= now + timedelta(days=30))
    return {"sources": len(sources), "facts": len(facts), "policies": len(policies), "expiring_soon": expiring}


@app.get("/api/knowledge/drift")
def get_drift_report(
    actor: Actor = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """
    Scans previously approved submissions and flags any that depend on
    outdated, superseded, or expired brand facts and policies.
    """
    return detect_policy_drift(db, actor.organization.id)


@app.get("/api/policies/conflicts")
def list_policy_conflicts(
    actor: Actor = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """
    Policy Conflict Intelligence:
    Identifies precedence ambiguities, contradictory directives, and overlapping scopes.
    """
    conflicts = detect_and_index_policy_conflicts(db, actor.organization.id)
    output = []
    for c in conflicts:
        pv_a = db.query(PolicyVersion).filter(PolicyVersion.id == c.policy_version_a_id).first()
        pv_b = db.query(PolicyVersion).filter(PolicyVersion.id == c.policy_version_b_id).first()
        output.append({
            "id": c.id,
            "conflict_type": c.conflict_type,
            "description": c.description,
            "status": c.status,
            "policy_a": {
                "id": pv_a.id,
                "version": pv_a.version,
                "scope": pv_a.scope,
                "precedence": pv_a.precedence,
                "rule_text": pv_a.rule_text,
            } if pv_a else None,
            "policy_b": {
                "id": pv_b.id,
                "version": pv_b.version,
                "scope": pv_b.scope,
                "precedence": pv_b.precedence,
                "rule_text": pv_b.rule_text,
            } if pv_b else None,
            "created_at": c.created_at,
        })
    return output


@app.post("/api/policies/conflicts/{conflict_id}/resolve")
def resolve_conflict_endpoint(
    conflict_id: str,
    payload: PolicyConflictResolve,
    actor: Actor = Depends(require_roles("admin", "brand_manager")),
    db: Session = Depends(get_db),
):
    """Brand managers review and resolve policy conflicts through a recorded audit workflow."""
    try:
        resolved = resolve_policy_conflict(
            db,
            actor.organization.id,
            conflict_id,
            actor.user.id,
            payload.resolution_notes,
            payload.winner_version_id,
            payload.new_precedence,
        )
        return {"id": resolved.id, "status": resolved.status, "resolved_at": resolved.resolved_at}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/impact/graph")
def get_impact_graph(
    actor: Actor = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """Change-Impact Re-review Graph mapping facts and policies to exact content revisions."""
    return build_change_impact_graph(db, actor.organization.id)


@app.get("/api/impact/tasks")
def list_rereview_tasks(
    actor: Actor = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """Lists targeted re-review work items so teams recheck only impacted content."""
    tasks = generate_targeted_rereview_tasks(db, actor.organization.id)
    output = []
    for t in tasks:
        sub = db.query(Submission).filter(Submission.id == t.submission_id).first()
        output.append({
            "id": t.id,
            "submission_id": t.submission_id,
            "title": sub.title if sub else "Untitled",
            "channel": sub.channel if sub else "Marketing",
            "trigger_type": t.trigger_type,
            "impact_summary": t.impact_summary,
            "status": t.status,
            "created_at": t.created_at,
        })
    return output


@app.post("/api/impact/tasks/{task_id}/resolve")
def resolve_rereview_task(
    task_id: str,
    actor: Actor = Depends(require_roles("admin", "reviewer", "brand_manager")),
    db: Session = Depends(get_db),
):
    """Mark a targeted re-review task as completed or dismissed."""
    task = db.query(ReReviewTask).filter(
        ReReviewTask.id == task_id,
        ReReviewTask.organization_id == actor.organization.id,
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Re-review task not found.")
    task.status = "completed"
    db.add(AuditEvent(
        organization_id=actor.organization.id,
        actor_id=actor.user.id,
        action="rereview.task_completed",
        entity_type="rereview_task",
        entity_id=task.id,
        metadata_json={"submission_id": task.submission_id},
    ))
    db.commit()
    return {"id": task.id, "status": task.status}


@app.post("/api/knowledge/facts", status_code=201)
def create_fact(payload: FactCreate, actor: Actor = Depends(require_roles("admin", "brand_manager")), db: Session = Depends(get_db)):
    source = EvidenceSource(
        organization_id=actor.organization.id, name=payload.source_name,
        source_version=payload.source_version, owner=payload.owner,
        approval_status="approved",
    )
    db.add(source)
    db.flush()
    latest = db.query(ApprovedFact).filter(
        ApprovedFact.organization_id == actor.organization.id,
        ApprovedFact.fact_key == payload.fact_key,
    ).order_by(ApprovedFact.version.desc()).first()
    if latest:
        latest.approval_status = "superseded"
    fact = ApprovedFact(
        organization_id=actor.organization.id, source_id=source.id,
        fact_key=payload.fact_key, version=(latest.version + 1 if latest else 1),
        label=payload.label, claim_text=payload.claim_text, owner=payload.owner,
        approval_status="approved",
    )
    db.add(fact)
    db.flush()
    db.add(AuditEvent(organization_id=actor.organization.id, actor_id=actor.user.id, action="fact.approved", entity_type="approved_fact", entity_id=fact.id, metadata_json={"version": fact.version, "source_id": source.id}))
    db.commit()
    db.refresh(fact)
    return pack_fact(fact)


@app.get("/api/submissions")
def list_submissions(actor: Actor = Depends(get_current_actor), db: Session = Depends(get_db)):
    items = db.query(Submission).filter(Submission.organization_id == actor.organization.id).order_by(Submission.created_at.desc()).all()
    return [{"id": s.id, "title": s.title, "channel": s.channel, "status": s.status, "created_at": s.created_at, "revision": latest_revision(db, s).revision_number if latest_revision(db, s) else 0} for s in items]


@app.post("/api/documents/extract")
async def extract_document_text(
    file: UploadFile = File(...),
    actor: Actor = Depends(require_roles("admin", "brand_manager", "creator")),
):
    """Extract clean text content from an uploaded PDF, DOCX, or text file."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds the 10MB limit.")
    text = extract_text_from_file(file.filename, content)
    return {
        "filename": file.filename,
        "content": text,
        "character_count": len(text),
        "word_count": len(text.split()),
    }


@app.post("/api/submissions", status_code=201)
def create_submission(payload: SubmissionCreate, actor: Actor = Depends(require_roles("admin", "brand_manager", "creator")), db: Session = Depends(get_db)):
    submission = Submission(organization_id=actor.organization.id, title=payload.title, channel=payload.channel, created_by=actor.user.id, status="draft")
    db.add(submission)
    db.flush()
    revision = SubmissionRevision(organization_id=actor.organization.id, submission_id=submission.id, revision_number=1, content_text=payload.content, content_hash=hash_content(payload.content), created_by=actor.user.id)
    db.add(revision)
    db.flush()
    db.add(AuditEvent(organization_id=actor.organization.id, actor_id=actor.user.id, action="submission.created", entity_type="submission", entity_id=submission.id, metadata_json={"revision_id": revision.id}))
    db.commit()
    return {"id": submission.id, "title": submission.title, "status": submission.status, "revision_id": revision.id, "revision_number": revision.revision_number}


@app.get("/api/submissions/{submission_id}")
def submission_detail(submission_id: str, actor: Actor = Depends(get_current_actor), db: Session = Depends(get_db)):
    submission = get_submission(db, actor, submission_id)
    revisions = db.query(SubmissionRevision).filter(SubmissionRevision.submission_id == submission.id).order_by(SubmissionRevision.revision_number.desc()).all()
    runs = db.query(ReviewRun).filter(ReviewRun.submission_id == submission.id).order_by(ReviewRun.created_at.desc()).all()
    decisions = db.query(ReviewDecision).filter(ReviewDecision.submission_id == submission.id).order_by(ReviewDecision.created_at.desc()).all()
    return {
        "id": submission.id, "title": submission.title, "channel": submission.channel, "status": submission.status,
        "revisions": [{"id": r.id, "number": r.revision_number, "content": r.content_text, "content_hash": r.content_hash, "created_at": r.created_at} for r in revisions],
        "review_runs": [pack_review(db, run) for run in runs],
        "decisions": [{"id": d.id, "decision": d.decision, "reviewer": db.query(User).filter(User.id == d.reviewer_id).first().display_name, "comments": d.comments, "created_at": d.created_at, "revision_id": d.revision_id} for d in decisions],
    }


@app.post("/api/submissions/{submission_id}/review")
def review_submission(submission_id: str, actor: Actor = Depends(require_roles("admin", "brand_manager", "creator")), db: Session = Depends(get_db)):
    submission = get_submission(db, actor, submission_id)
    if submission.status in {"in_review", "approved", "rejected"}:
        raise HTTPException(status_code=409, detail="This submission is already in the approval workflow. Create a new revision before reviewing again.")
    revision = latest_revision(db, submission)
    run = run_review(db, actor, submission, revision)
    db.commit()
    return pack_review(db, run)


@app.post("/api/submissions/{submission_id}/revisions", status_code=201)
def revise_submission(submission_id: str, payload: RevisionCreate, actor: Actor = Depends(require_roles("admin", "brand_manager", "creator")), db: Session = Depends(get_db)):
    submission = get_submission(db, actor, submission_id)
    if submission.status in {"in_review", "approved", "rejected"}:
        raise HTTPException(status_code=409, detail="A submission in or past human review cannot be edited. Request changes first or start a new submission.")
    latest = latest_revision(db, submission)
    revision = SubmissionRevision(organization_id=actor.organization.id, submission_id=submission.id, revision_number=latest.revision_number + 1, content_text=payload.content, content_hash=hash_content(payload.content), created_by=actor.user.id)
    db.add(revision)
    submission.status = "draft"
    db.add(AuditEvent(organization_id=actor.organization.id, actor_id=actor.user.id, action="submission.revised", entity_type="submission", entity_id=submission.id, metadata_json={"revision_number": revision.revision_number, "supersedes_revision_id": latest.id}))
    db.commit()
    db.refresh(revision)
    return {"id": revision.id, "revision_number": revision.revision_number, "content_hash": revision.content_hash}


@app.post("/api/submissions/{submission_id}/submit")
def submit_for_approval(submission_id: str, actor: Actor = Depends(require_roles("admin", "brand_manager", "creator")), db: Session = Depends(get_db)):
    submission = get_submission(db, actor, submission_id)
    if submission.status == "in_review":
        raise HTTPException(status_code=409, detail="This submission is already awaiting a reviewer.")
    revision = latest_revision(db, submission)
    run = db.query(ReviewRun).filter(ReviewRun.revision_id == revision.id).order_by(ReviewRun.created_at.desc()).first()
    if run is None:
        raise HTTPException(status_code=409, detail="Run a compliance review on the latest revision before submitting it.")
    submission.status = "in_review"
    db.add(AuditEvent(organization_id=actor.organization.id, actor_id=actor.user.id, action="submission.submitted_for_review", entity_type="submission", entity_id=submission.id, metadata_json={"revision_id": revision.id, "review_run_id": run.id}))
    db.commit()
    return {"id": submission.id, "status": submission.status, "revision_id": revision.id}


@app.get("/api/approvals")
def approvals(actor: Actor = Depends(get_current_actor), db: Session = Depends(get_db)):
    items = db.query(Submission).filter(Submission.organization_id == actor.organization.id, Submission.status == "in_review").order_by(Submission.created_at).all()
    output = []
    for item in items:
        revision = latest_revision(db, item)
        run = db.query(ReviewRun).filter(ReviewRun.revision_id == revision.id).order_by(ReviewRun.created_at.desc()).first()
        creator = db.query(User).filter(User.id == item.created_by).first()
        output.append({"id": item.id, "title": item.title, "channel": item.channel, "status": item.status, "revision_number": revision.revision_number, "content": revision.content_text, "creator": creator.display_name, "review": pack_review(db, run) if run else None})
    return output


@app.post("/api/submissions/{submission_id}/decisions")
def decide(submission_id: str, payload: DecisionCreate, actor: Actor = Depends(require_roles("admin", "reviewer")), db: Session = Depends(get_db)):
    if payload.decision not in {"approved", "rejected", "needs_changes"}:
        raise HTTPException(status_code=422, detail="Decision must be approved, rejected, or needs_changes.")
    submission = get_submission(db, actor, submission_id)
    if submission.status != "in_review":
        raise HTTPException(status_code=409, detail="Only submissions awaiting human review can receive a decision.")
    revision = latest_revision(db, submission)
    run = db.query(ReviewRun).filter(ReviewRun.revision_id == revision.id).order_by(ReviewRun.created_at.desc()).first()
    if run is None:
        raise HTTPException(status_code=409, detail="The current revision has no completed review run.")
    if payload.override_justification is not None and not payload.override_justification.strip():
        raise HTTPException(status_code=422, detail="Override justification cannot be blank.")
    material_findings = db.query(Finding).filter(Finding.review_run_id == run.id, Finding.status.in_(["contradicted", "policy_violation"])).count()
    if payload.decision == "approved" and material_findings and not (payload.override_justification or "").strip():
        raise HTTPException(status_code=422, detail="Approving material findings requires an override justification.")
    decision = ReviewDecision(
        organization_id=actor.organization.id, submission_id=submission.id,
        revision_id=revision.id, review_run_id=run.id, reviewer_id=actor.user.id,
        decision=payload.decision, comments=payload.comments,
        override_justification=payload.override_justification,
    )
    db.add(decision)
    submission.status = payload.decision
    db.add(AuditEvent(organization_id=actor.organization.id, actor_id=actor.user.id, action=f"review.{payload.decision}", entity_type="submission", entity_id=submission.id, metadata_json={"revision_id": revision.id, "review_run_id": run.id, "override": bool(payload.override_justification)}))
    db.commit()
    return {"id": decision.id, "decision": decision.decision, "revision_id": decision.revision_id, "review_run_id": decision.review_run_id, "created_at": decision.created_at}
