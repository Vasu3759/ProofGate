import re
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models import AuditEvent, BrandPolicy, PolicyConflict, PolicyVersion, User


def detect_and_index_policy_conflicts(db: Session, organization_id: str) -> list[PolicyConflict]:
    """
    Policy Conflict Intelligence Engine:
    Detects:
    1. Scope & Precedence Overlaps: When two active policies share the same scope
       and rule domain but have conflicting precedence or identical precedence.
    2. Contradictory Directives: E.g., one policy allows comparative claims under disclaimer,
       while another strictly forbids all comparative/superlative claims.
    """
    now = datetime.now(timezone.utc)
    active_versions = db.query(PolicyVersion).filter(
        PolicyVersion.organization_id == organization_id,
        PolicyVersion.approval_status == "approved",
        PolicyVersion.effective_at <= now,
    ).order_by(PolicyVersion.precedence.asc()).all()

    existing_conflicts = {
        (c.policy_version_a_id, c.policy_version_b_id): c
        for c in db.query(PolicyConflict).filter(
            PolicyConflict.organization_id == organization_id,
            PolicyConflict.status == "unresolved",
        ).all()
    }

    detected_conflicts = []

    for i in range(len(active_versions)):
        for j in range(i + 1, len(active_versions)):
            p_a = active_versions[i]
            p_b = active_versions[j]

            pair_key = (p_a.id, p_b.id)
            alt_pair_key = (p_b.id, p_a.id)
            if pair_key in existing_conflicts or alt_pair_key in existing_conflicts:
                continue

            text_a = p_a.rule_text.lower()
            text_b = p_b.rule_text.lower()
            conflict_found = False
            c_type = ""
            desc = ""

            # Check 1: Identical Scope & Conflicting Precedence Ambiguity
            if p_a.scope == p_b.scope and p_a.precedence == p_b.precedence:
                conflict_found = True
                c_type = "precedence_ambiguity"
                desc = (
                    f"Ambiguous precedence conflict: Policy '{p_a.policy_id}' and '{p_b.policy_id}' "
                    f"both operate within scope '{p_a.scope}' with identical priority tier {p_a.precedence}. "
                    "Precedence must be explicitly sequenced."
                )

            # Check 2: Direct Substantive Contradictions (e.g. Guarantee/Comparative rules)
            guarantee_terms = ["guarantee", "superlative", "comparative", "promise"]
            if any(t in text_a for t in guarantee_terms) and any(t in text_b for t in guarantee_terms):
                a_prohibits = any(w in text_a for w in ["prohibit", "not be published", "never", "must not"])
                b_permits = any(w in text_b for w in ["permitted with", "allowed if", "disclaimer", "exception"])
                if (a_prohibits and b_permits) or (p_a.precedence >= p_b.precedence and a_prohibits):
                    conflict_found = True
                    c_type = "scope_contradiction"
                    desc = (
                        f"Contradictory directives detected between Scope '{p_a.scope}' and '{p_b.scope}': "
                        f"One rule prohibits promotional guarantees while another permits them with conditions. "
                        "Brand managers must establish precedence before review execution."
                    )

            if conflict_found:
                conflict = PolicyConflict(
                    organization_id=organization_id,
                    policy_version_a_id=p_a.id,
                    policy_version_b_id=p_b.id,
                    conflict_type=c_type,
                    description=desc,
                    status="unresolved",
                )
                db.add(conflict)
                detected_conflicts.append(conflict)

    if detected_conflicts:
        db.flush()

    return db.query(PolicyConflict).filter(
        PolicyConflict.organization_id == organization_id,
        PolicyConflict.status == "unresolved",
    ).all()


def resolve_policy_conflict(
    db: Session,
    organization_id: str,
    conflict_id: str,
    user_id: str,
    resolution_notes: str,
    winner_version_id: str | None = None,
    new_precedence: int | None = None,
) -> PolicyConflict:
    """Resolve an identified policy conflict with an explicit audit log."""
    conflict = db.query(PolicyConflict).filter(
        PolicyConflict.id == conflict_id,
        PolicyConflict.organization_id == organization_id,
    ).first()
    if not conflict:
        raise ValueError("Policy conflict not found.")

    if winner_version_id and new_precedence is not None:
        winner = db.query(PolicyVersion).filter(PolicyVersion.id == winner_version_id).first()
        if winner:
            winner.precedence = new_precedence
            db.add(winner)

    conflict.status = "resolved"
    conflict.resolved_by = user_id
    conflict.resolution_notes = resolution_notes
    conflict.resolved_at = datetime.now(timezone.utc)

    db.add(AuditEvent(
        organization_id=organization_id,
        actor_id=user_id,
        action="policy.conflict_resolved",
        entity_type="policy_conflict",
        entity_id=conflict.id,
        metadata_json={
            "conflict_type": conflict.conflict_type,
            "resolution_notes": resolution_notes,
            "winner_version_id": winner_version_id,
            "new_precedence": new_precedence,
        },
    ))
    db.commit()
    db.refresh(conflict)
    return conflict
