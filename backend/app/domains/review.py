import re
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.domains.ai_engine import call_llm_verification, semantic_nli_fallback
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
    rationale: str | None = None,
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
            rationale=rationale or "Aligns the statement with approved organizational guidance.",
        ))
    return finding


def run_review(db: Session, actor: Actor, submission: Submission, revision: SubmissionRevision):
    """
    Hybrid Three-Tier Review Pipeline:
    - Tier 1: Deterministic rules (numbers, disclosures, strict patterns)
    - Tier 2: Evidence Ledger retrieval & Semantic-NLI verification
    - Tier 3: Contextual LLM evaluation (tone, nuance, intent-preserving suggestions)
    """
    run = ReviewRun(
        organization_id=actor.organization.id,
        submission_id=submission.id,
        revision_id=revision.id,
        pipeline_version="hybrid-v2-ai",
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

    # Prepare evidence context for AI
    facts_payload = [
        {"fact_key": f.fact_key, "label": f.label, "claim_text": f.claim_text, "version": f.version}
        for f in facts
    ]
    policies_payload = [p.rule_text for p in policy_versions]

    # Attempt Tier 3 (LLM) or fallback to Tier 2 (Semantic NLI)
    ai_result = call_llm_verification(text, facts_payload, policies_payload)
    used_tier = "tier-3-llm"
    if not ai_result:
        ai_result = semantic_nli_fallback(text, facts_payload, policies_payload)
        used_tier = "tier-2-nli"

    applicable_policy = next(
        (p for p in policy_versions if "guarantee" in p.rule_text.lower() or "unsupported" in p.rule_text.lower()),
        None,
    )

    # Ingest AI findings with source evidence linkage
    recorded_claims = set()
    for item in ai_result.get("findings", []):
        claim_str = item["claim_text"]
        matched_key = item.get("matched_fact_key")
        fact = facts_by_key.get(matched_key) if matched_key else None
        
        _add_finding(
            db,
            actor,
            run,
            claim=claim_str,
            status=item["status"],
            severity=item["severity"],
            explanation=item["explanation"],
            fact=fact,
            suggestion=item.get("suggested_text"),
            rationale=item.get("rationale"),
            policy=applicable_policy if item["status"] == "policy_violation" else None,
        )
        recorded_claims.add(claim_str.lower())

    # Complement with Tier 1 Deterministic Verification (value match & exact citations)
    for fact_key, pattern in VALUE_CLAIMS.items():
        fact = facts_by_key.get(fact_key)
        source = VALUE_SOURCES[fact_key].search(fact.claim_text) if fact else None
        for match in pattern.finditer(text):
            claim_text_val = match.group(0)
            if claim_text_val.lower() in recorded_claims:
                continue
            if not fact or not source:
                _add_finding(
                    db, actor, run, claim=claim_text_val, status="unverified",
                    severity="high", explanation="No current approved numeric source value is available for comparison.", fact=fact
                )
                continue
            claim_value = match.group(1)
            source_value = source.group(1)
            equal = _normalized_value(claim_value) == _normalized_value(source_value)
            if equal:
                _add_finding(
                    db, actor, run, claim=claim_text_val, status="supported",
                    severity="info", explanation=f"This value is backed by the approved record: {fact.claim_text}", fact=fact
                )
            else:
                sug = _suggestion(fact_key, fact)
                _add_finding(
                    db, actor, run, claim=claim_text_val, status="contradicted",
                    severity="critical", explanation=f"The value conflicts with the current approved record: {fact.claim_text}",
                    fact=fact, suggestion=sug
                )

    has_material_findings = db.query(Finding).filter(
        Finding.review_run_id == run.id,
        Finding.status.in_(["contradicted", "policy_violation"]),
    ).count()
    submission.status = "needs_changes" if has_material_findings else "reviewed"

    metadata = {
        "revision_id": revision.id,
        "review_run_id": run.id,
        "pipeline_engine": used_tier,
        "tone_score": ai_result.get("tone_score", 100),
        "detected_tone": ai_result.get("detected_tone", "Neutral"),
        "tone_summary": ai_result.get("tone_summary", ""),
    }
    db.add(AuditEvent(
        organization_id=actor.organization.id,
        actor_id=actor.user.id,
        action="review.completed",
        entity_type="submission",
        entity_id=submission.id,
        metadata_json=metadata,
    ))
    db.flush()
    return run
