from datetime import datetime, timezone
import pytest
from app.domains.ai_engine import derive_suggestion, parse_numeric_fact


def headers(user="alex@meridianlabs.example"):
    return {"X-Demo-User": user, "X-Organization": "meridian-labs"}


def test_85_market_claim_is_supported_not_contradicted(client):
    """
    Regression test: Content claiming the exact approved 85 markets (from seed)
    must be marked as supported, NOT contradicted.
    """
    res = client.post(
        "/api/submissions",
        headers=headers(),
        json={
            "title": "85 Markets Verified Campaign",
            "channel": "LinkedIn",
            "content": "MeridianPay is proudly available in 85 supported markets.",
        },
    )
    assert res.status_code == 201
    submission_id = res.json()["id"]

    review_res = client.post(f"/api/submissions/{submission_id}/review", headers=headers())
    assert review_res.status_code == 200
    review_data = review_res.json()

    # Finding for 85 supported markets should be supported
    market_findings = [f for f in review_data["findings"] if "85 supported markets" in f["claim_text"]]
    assert len(market_findings) > 0
    assert all(f["status"] == "supported" for f in market_findings)
    # Ensure no contradicted findings
    assert not any(f["status"] == "contradicted" for f in review_data["findings"])


def test_fact_based_dynamic_suggestion(client):
    """
    Regression test: Suggestions must be derived dynamically from the approved record,
    not hardcoded (e.g. 1.5% fee from v1 or updated fee from new fact).
    """
    fee_fact = "International transfers are subject to a 1.5% processing fee."
    derived = derive_suggestion("fee", fee_fact)
    assert derived == "international transfers, subject to a 1.5% processing fee"

    markets_fact = "MeridianPay is available in 85 supported markets."
    derived_markets = derive_suggestion("markets", markets_fact)
    assert derived_markets == "85 supported markets"

    # Test in review flow for a contradicted claim
    res = client.post(
        "/api/submissions",
        headers=headers(),
        json={
            "title": "Free Fee Campaign",
            "channel": "LinkedIn",
            "content": "Our transfers are completely free of charge.",
        },
    )
    submission_id = res.json()["id"]
    review = client.post(f"/api/submissions/{submission_id}/review", headers=headers()).json()

    fee_findings = [f for f in review["findings"] if f["status"] == "contradicted"]
    assert len(fee_findings) > 0
    sug_text = fee_findings[0]["suggestion"]["text"]
    assert "1.5%" in sug_text or "processing fee" in sug_text


def test_targeted_policy_and_fact_drift(client):
    """
    Regression test: Only approved submissions that actually depend on a changed/expired
    fact or updated policy version are flagged for drift.
    """
    # Create two approved submissions:
    # Sub A cites 'settlement'
    res_a = client.post("/api/submissions", headers=headers(), json={
        "title": "Sub A - Settlement Only",
        "channel": "Web",
        "content": "Transfers settle in 1–2 business days.",
    })
    sub_a_id = res_a.json()["id"]
    client.post(f"/api/submissions/{sub_a_id}/review", headers=headers())
    client.post(f"/api/submissions/{sub_a_id}/submit", headers=headers())
    client.post(f"/api/submissions/{sub_a_id}/decisions", headers=headers("dana@meridianlabs.example"), json={
        "decision": "approved", "comments": "Approved settlement wording"
    })

    # Sub B cites 'fee'
    res_b = client.post("/api/submissions", headers=headers(), json={
        "title": "Sub B - Fee Campaign",
        "channel": "Web",
        "content": "International transfers are subject to a 1.5% processing fee.",
    })
    sub_b_id = res_b.json()["id"]
    client.post(f"/api/submissions/{sub_b_id}/review", headers=headers())
    client.post(f"/api/submissions/{sub_b_id}/submit", headers=headers())
    client.post(f"/api/submissions/{sub_b_id}/decisions", headers=headers("dana@meridianlabs.example"), json={
        "decision": "approved", "comments": "Approved fee wording"
    })

    # Now add a new version of 'fee' (v2)
    client.post("/api/knowledge/facts", headers=headers("morgan@meridianlabs.example"), json={
        "fact_key": "fee",
        "label": "Transfer fee v2",
        "claim_text": "Subject to a 2.5% processing fee",
        "source_name": "Pricing Update 2026",
        "source_version": "v2.0",
        "owner": "Finance",
    })

    # Check drift report: Sub B must drift; Sub A must NOT drift!
    drift_res = client.get("/api/knowledge/drift", headers=headers("morgan@meridianlabs.example"))
    assert drift_res.status_code == 200
    drift_items = drift_res.json()
    drift_sub_ids = [d["submission_id"] for d in drift_items]

    assert sub_b_id in drift_sub_ids, "Sub B depends on fee v1 and must be flagged for drift!"
    assert sub_a_id not in drift_sub_ids, "Sub A depends only on settlement and must NOT drift!"


def test_review_metadata_tied_to_correct_run(client):
    """
    Regression test: Audit metadata and AI metadata are tied to the exact review run,
    not bleeding across revisions or submissions.
    """
    res = client.post("/api/submissions", headers=headers(), json={
        "title": "Multi-Revision Test",
        "channel": "Twitter",
        "content": "MeridianPay offers completely free international transfers.",
    })
    sub_id = res.json()["id"]

    # Run 1
    rev1 = client.post(f"/api/submissions/{sub_id}/review", headers=headers()).json()
    run1_id = rev1["id"]
    assert rev1["ai_metadata"]["pipeline_engine"] in ["tier-3-llm", "tier-2-nli", "deterministic-v1"]

    # Revise
    client.post(f"/api/submissions/{sub_id}/revisions", headers=headers(), json={
        "content": "Transfers settle in 1–2 business days.",
    })

    # Run 2
    rev2 = client.post(f"/api/submissions/{sub_id}/review", headers=headers()).json()
    run2_id = rev2["id"]
    assert run1_id != run2_id
    assert rev2["revision_id"] != rev1["revision_id"]
    assert rev2["ai_metadata"]["pipeline_engine"] in ["tier-3-llm", "tier-2-nli", "deterministic-v1"]
