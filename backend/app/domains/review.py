import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from sqlalchemy.orm import Session

from app.domains.ai_engine import (
    call_llm_verification,
    derive_suggestion,
    finding_claim_is_grounded,
    parse_numeric_fact,
    semantic_nli_fallback,
    suggestion_matches_fact,
)
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

VALUE_CLAIMS = {
    "fee": re.compile(r"\b(\d+(?:\.\d+)?)%\s+(?:processing\s+)?fee\b", re.I),
    "settlement": re.compile(r"\b(\d+\s*[–-]\s*\d+\s+business\s+days)\b", re.I),
    "markets": re.compile(r"\b(\d+)\s+supported\s+markets\b", re.I),
}


def _normalized_value(value: str) -> str:
    return re.sub(r"[^0-9.]", "", value)


def _normalized_text(value: str) -> str:
    return " ".join(value.split()).casefold()


def _fact_supports_finding(claim: str, status: str, fact: ApprovedFact) -> bool:
    """
    Verify whether the cited ApprovedFact genuinely supports, contradicts, or relates
    to the specific finding before attaching evidence.
    """
    if not fact or status not in {"supported", "contradicted"}:
        return False
    approved = parse_numeric_fact(fact.claim_text)

    if fact.fact_key == "fee":
        approved_fee = approved.get("fee")
        claim_fee = re.search(r"\b(\d+(?:\.\d+)?)\s*%", claim)
        if approved_fee is not None and claim_fee:
            try:
                equal = Decimal(claim_fee.group(1)) == Decimal(str(approved_fee))
            except InvalidOperation:
                return False
            return equal if status == "supported" else not equal
        if approved_fee is not None and re.search(r"\b(?:free|zero\s+fees?|no\s+fees?)\b", claim, re.I):
            try:
                return status == "contradicted" and Decimal(str(approved_fee)) > 0
            except InvalidOperation:
                return False
    elif fact.fact_key == "settlement":
        approved_range = approved.get("settlement")
        claim_range = parse_numeric_fact(claim).get("settlement")
        if approved_range and claim_range:
            normalize = lambda value: re.sub(r"\s+", "", value).replace("-", "–").casefold()
            equal = normalize(approved_range) == normalize(claim_range)
            return equal if status == "supported" else not equal
        if approved_range and re.search(r"\b(?:instant(?:ly)?|real[- ]time|same[- ]day)\b", claim, re.I):
            return status == "contradicted"
    elif fact.fact_key == "markets":
        approved_count = approved.get("markets")
        claim_count = re.search(
            r"\b(?:(over|more than)\s*)?(\d+)\+?\s*(?:supported\s+)?(?:markets|countries)\b",
            claim,
            re.I,
        )
        if approved_count is not None and claim_count:
            claimed = int(claim_count.group(2))
            if claimed > approved_count:
                return status == "contradicted"
            if claimed == approved_count and not claim_count.group(1):
                return status == "supported"

    return False


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

    if fact and _fact_supports_finding(claim, status, fact):
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
    ).order_by(PolicyVersion.precedence.asc()).all()

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

    facts_payload = [
        {"fact_key": f.fact_key, "label": f.label, "claim_text": f.claim_text, "version": f.version}
        for f in facts
    ]
    policies_payload = [p.rule_text for p in policy_versions]

    ai_result = call_llm_verification(text, facts_payload, policies_payload)
    used_tier = "tier-3-llm"
    if not ai_result:
        ai_result = semantic_nli_fallback(text, facts_payload, policies_payload)
        used_tier = "tier-2-nli"

    applicable_policy = next(
        (p for p in policy_versions if "guarantee" in p.rule_text.lower() or "unsupported" in p.rule_text.lower()),
        None,
    )

    recorded_claims = set()
    for item in ai_result.get("findings", []):
        claim_str = item["claim_text"]
        if not finding_claim_is_grounded(claim_str, text):
            continue

        if item["status"] == "supported" or any(
            _normalized_text(match.group(0)) == _normalized_text(claim_str)
            for pattern in VALUE_CLAIMS.values()
            if (match := pattern.search(claim_str))
        ):
            continue

        matched_key = item.get("matched_fact_key")
        fact = facts_by_key.get(matched_key) if matched_key else None

        finding_status = item["status"]
        finding_explanation = item["explanation"]
        if finding_status == "contradicted" and not _fact_supports_finding(claim_str, finding_status, fact):
            finding_status = "unverified"
            finding_explanation = (
                "No applicable approved record establishes a contradiction for this claim. "
                "Treat it as unverified until authoritative evidence is available."
            )
            fact = None
        elif finding_status not in {"supported", "contradicted"}:
            fact = None

        sug = item.get("suggested_text")
        if finding_status == "unverified" and not fact:
            sug = None
        elif fact and sug and not suggestion_matches_fact(sug, fact.fact_key, fact.claim_text):
            sug = derive_suggestion(fact.fact_key, fact.claim_text)
        elif fact and not sug:
            sug = derive_suggestion(fact.fact_key, fact.claim_text)

        _add_finding(
            db,
            actor,
            run,
            claim=claim_str,
            status=finding_status,
            severity=item["severity"],
            explanation=finding_explanation,
            fact=fact,
            suggestion=sug,
            rationale=item.get("rationale"),
            policy=applicable_policy if item["status"] == "policy_violation" else None,
        )
        recorded_claims.add(claim_str.lower())

    for fact_key, pattern in VALUE_CLAIMS.items():
        fact = facts_by_key.get(fact_key)
        params = parse_numeric_fact(fact.claim_text) if fact else {}
        for match in pattern.finditer(text):
            claim_text_val = match.group(0)
            if claim_text_val.lower() in recorded_claims:
                continue
            if not fact or fact_key not in params:
                _add_finding(
                    db, actor, run, claim=claim_text_val, status="unverified",
                    severity="high", explanation="No current approved numeric source value is available for comparison.", fact=fact
                )
                continue

            claim_value = match.group(1)
            source_value = str(params[fact_key])
            equal = _normalized_value(claim_value) == _normalized_value(source_value)
            if equal:
                _add_finding(
                    db, actor, run, claim=claim_text_val, status="supported",
                    severity="info", explanation=f"This value is backed by the approved record: {fact.claim_text}", fact=fact
                )
            elif fact_key == "markets" and int(claim_value) < int(source_value):
                _add_finding(
                    db, actor, run, claim=claim_text_val, status="unverified",
                    severity="high",
                    explanation="The approved record lists broader market coverage but does not establish this narrower count.",
                    fact=None,
                )
            else:
                sug = derive_suggestion(fact_key, fact.claim_text)
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
