import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.domains.auth import Actor
from app.models import (
    ApprovedFact,
    AuditEvent,
    CorrectionSuggestion,
    Finding,
    FindingEvidence,
    FindingPolicy,
    PolicyVersion,
    ReviewRun,
    ReviewRunPolicy,
    Submission,
    SubmissionRevision,
)

CLAIM_RULES = {
    "fee": re.compile(
        r"\b(?:completely\s+)?free(?:\s+of\s+(?:fees?|charge))?\s+(?:international\s+)?transfers?\b|\btransfers?\s+(?:are\s+)?free\b",
        re.I,
    ),
    "settlement": re.compile(r"\bavailable\s+instantly\b|\binstant(?:ly)?\b|\bsame[- ]day\b", re.I),
    "markets": re.compile(r"\b(?:over|more than)\s+(\d+)\s+(?:countries|markets)\b|\b(\d+)\+\s*(?:countries|markets)\b", re.I),
}
VALUE_CLAIMS = {
    "fee": re.compile(r"\b(\d+(?:\.\d+)?)%\s+(?:processing\s+)?fee\b", re.I),
    "settlement": re.compile(r"\b(\d+\s*[–-]\s*\d+\s+business\s+days)\b", re.I),
    "markets": re.compile(r"\b(\d+)\s+supported\s+markets\b", re.I),
}
VALUE_SOURCES = {
    "fee": re.compile(r"\b(\d+(?:\.\d+)?)%", re.I),
    "settlement": re.compile(r"\b(\d+\s*[–-]\s*\d+\s+business\s+days)\b", re.I),
    "markets": re.compile(r"\b(\d+)\s+supported\s+markets\b", re.I),
}
UNSUPPORTED_PROMISE = re.compile(r"\b(?:guaranteed|risk[- ]free|the\s+best|number\s+one|#1)\b", re.I)


def _normalized_value(value: str) -> str:
    return re.sub(r"[^0-9.]", "", value)


def _suggestion(fact_key: str, fact: ApprovedFact) -> str | None:
    source = VALUE_SOURCES[fact_key].search(fact.claim_text)
    if not source:
        return None
    value = source.group(1).replace("-", "–")
    if fact_key == "fee":
        return f"international transfers, subject to a {value}% processing fee"
    if fact_key == "settlement":
        return f"available with settlement in {value}"
    return f"{value} supported markets"


def _add_finding(
    db: Session,
    actor: Actor,
    run: ReviewRun,
    *,
    claim: str,
    status: str,
    severity: str,
    explanation: str,
    fact: ApprovedFact | None = None,
    suggestion: str | None = None,
    policy: PolicyVersion | None = None,
) -> Finding:
    finding = Finding(
        organization_id=actor.organization.id,
        review_run_id=run.id,
        finding_type="policy_violation" if status == "policy_violation" else "claim_verification",
        severity=severity,
        claim_text=claim,
        status=status,
        explanation=explanation,
    )
    db.add(finding)
    db.flush()
    if fact:
        db.add(FindingEvidence(
            finding_id=finding.id,
            fact_id=fact.id,
            fact_version=fact.version,
            source_id=fact.source_id,
            excerpt=fact.claim_text,
        ))
    if policy:
        db.add(FindingPolicy(finding_id=finding.id, policy_version_id=policy.id))
    if suggestion:
        db.add(CorrectionSuggestion(
            finding_id=finding.id,
            suggested_text=suggestion,
            rationale="Aligns the statement with approved organizational guidance.",
        ))
    return finding


def run_review(db: Session, actor: Actor, submission: Submission, revision: SubmissionRevision):
    run = ReviewRun(
        organization_id=actor.organization.id,
        submission_id=submission.id,
        revision_id=revision.id,
        pipeline_version="deterministic-v1",
    )
    db.add(run)
    db.flush()

    policy_versions = db.query(PolicyVersion).filter(
        PolicyVersion.organization_id == actor.organization.id,
        PolicyVersion.approval_status == "approved",
    ).all()
    for policy in policy_versions:
        db.add(ReviewRunPolicy(review_run_id=run.id, policy_version_id=policy.id))

    now = datetime.now(timezone.utc)
    facts = db.query(ApprovedFact).filter(
        ApprovedFact.organization_id == actor.organization.id,
        ApprovedFact.approval_status == "approved",
        ApprovedFact.effective_at <= now,
    ).all()
    facts_by_key = {fact.fact_key: fact for fact in facts}
    text = revision.content_text

    for fact_key, pattern in CLAIM_RULES.items():
        fact = facts_by_key.get(fact_key)
        for match in pattern.finditer(text):
            claim = match.group(0)
            suggestion = None
            if fact is None:
                status, severity = "unverified", "high"
                explanation = "No current approved source record was found. Missing evidence is not proof that the claim is false."
            elif fact.expires_at and fact.expires_at <= now:
                status, severity = "unverified", "high"
                explanation = "The matching approved fact has expired, so this claim cannot be checked against current evidence."
            elif fact_key == "markets":
                source = VALUE_SOURCES[fact_key].search(fact.claim_text)
                claimed = next((value for value in match.groups() if value), None)
                if source and claimed and int(claimed) > int(source.group(1)):
                    status, severity = "contradicted", "critical"
                    explanation = f"The claim exceeds the current approved market count: {fact.claim_text}"
                    suggestion = _suggestion(fact_key, fact)
                else:
                    status, severity = "unverified", "high"
                    explanation = f"The approved record does not establish this broader wording: {fact.claim_text}"
            else:
                source = VALUE_SOURCES[fact_key].search(fact.claim_text)
                if source:
                    status, severity = "contradicted", "critical"
                    explanation = f"The claim conflicts with the current approved record: {fact.claim_text}"
                    suggestion = _suggestion(fact_key, fact)
                else:
                    status, severity = "unverified", "high"
                    explanation = f"The approved record does not provide enough detail to verify this claim: {fact.claim_text}"
            _add_finding(db, actor, run, claim=claim, status=status, severity=severity, explanation=explanation, fact=fact, suggestion=suggestion)

    for fact_key, pattern in VALUE_CLAIMS.items():
        fact = facts_by_key.get(fact_key)
        source = VALUE_SOURCES[fact_key].search(fact.claim_text) if fact else None
        for match in pattern.finditer(text):
            if not fact or not source:
                _add_finding(db, actor, run, claim=match.group(0), status="unverified", severity="high", explanation="No current approved numeric source value is available for comparison.", fact=fact)
                continue
            claim_value = match.group(1)
            source_value = source.group(1)
            equal = _normalized_value(claim_value) == _normalized_value(source_value)
            suggestion = None
            if equal:
                status, severity = "supported", "info"
                explanation = f"This value is backed by the approved record: {fact.claim_text}"
            elif fact_key == "markets" and int(claim_value) < int(source_value):
                status, severity = "unverified", "high"
                explanation = f"The approved record does not establish this exact market count: {fact.claim_text}"
            else:
                status, severity = "contradicted", "critical"
                explanation = f"The value conflicts with the current approved record: {fact.claim_text}"
                if fact_key in {"fee", "settlement"}:
                    suggestion = _suggestion(fact_key, fact)
            _add_finding(db, actor, run, claim=match.group(0), status=status, severity=severity, explanation=explanation, fact=fact, suggestion=suggestion)

    applicable = next((p for p in policy_versions if "guarantee" in p.rule_text.lower() or "unsupported" in p.rule_text.lower()), None)
    for match in UNSUPPORTED_PROMISE.finditer(text):
        phrase = match.group(0)
        _add_finding(
            db, actor, run, claim=phrase, status="unverified", severity="high",
            explanation="This promotional promise has no matching approved evidence record. It is unverified, not established as false.",
            suggestion="Remove this unsupported promise or provide an approved source.",
        )
        _add_finding(
            db, actor, run, claim=phrase, status="policy_violation", severity="high",
            explanation="The active brand policy prohibits unsupported promotional guarantees. This phrase also lacks an approved evidence record.",
            policy=applicable,
        )

    has_material_findings = db.query(Finding).filter(
        Finding.review_run_id == run.id,
        Finding.status.in_(["contradicted", "policy_violation"]),
    ).count()
    submission.status = "needs_changes" if has_material_findings else "reviewed"
    db.add(AuditEvent(
        organization_id=actor.organization.id,
        actor_id=actor.user.id,
        action="review.completed",
        entity_type="submission",
        entity_id=submission.id,
        metadata_json={"revision_id": revision.id, "review_run_id": run.id},
    ))
    db.flush()
    return run
