from app.models import Submission, SubmissionRevision
from conftest import headers


DEMO_CLAIM = "MeridianPay offers completely free international transfers, available instantly in over 150 countries."


def create_and_review(client, text=DEMO_CLAIM):
    response = client.post("/api/submissions", headers=headers(), json={"title": "Launch post", "channel": "LinkedIn", "content": text})
    assert response.status_code == 201
    submission_id = response.json()["id"]
    review = client.post(f"/api/submissions/{submission_id}/review", headers=headers())
    assert review.status_code == 200
    return submission_id, review.json()


def test_review_citations_are_pinned_to_approved_facts(client):
    _, review = create_and_review(client)
    assert len(review["findings"]) == 3
    assert {item["status"] for item in review["findings"]} == {"contradicted"}
    assert {item["evidence"]["fact_key"] for item in review["findings"]} == {"fee", "settlement", "markets"}
    assert all(item["evidence"]["fact_version"] == 1 for item in review["findings"])
    assert review["policies"][0]["version"] == 1


def test_tenant_and_role_boundaries(client):
    response = client.post("/api/knowledge/facts", headers=headers(), json={
        "fact_key": "fee", "label": "Fee", "claim_text": "Fee is 2%.",
        "source_name": "Pricing", "source_version": "v2", "owner": "Finance",
    })
    assert response.status_code == 403
    assert client.get("/api/submissions", headers={"X-Demo-User": "alex@meridianlabs.example", "X-Organization": "other-org"}).status_code == 401
    submission_id, _ = create_and_review(client)
    client.post(f"/api/submissions/{submission_id}/submit", headers=headers())
    response = client.post(f"/api/submissions/{submission_id}/decisions", headers=headers(), json={"decision": "approved"})
    assert response.status_code == 403


def test_decision_pins_revision_and_changes_require_a_new_review(client):
    submission_id, first_review = create_and_review(client)
    submitted = client.post(f"/api/submissions/{submission_id}/submit", headers=headers())
    assert submitted.status_code == 200
    requested = client.post(f"/api/submissions/{submission_id}/decisions", headers=headers("dana@meridianlabs.example"), json={"decision": "needs_changes", "comments": "Please correct the claims."})
    assert requested.status_code == 200
    assert requested.json()["revision_id"] == first_review["revision_id"]

    edited = client.post(f"/api/submissions/{submission_id}/revisions", headers=headers(), json={"content": "MeridianPay transfers are subject to a 1.5% processing fee, settle in 1–2 business days, and are available in 85 supported markets."})
    assert edited.status_code == 201
    second_review = client.post(f"/api/submissions/{submission_id}/review", headers=headers())
    assert second_review.status_code == 200
    assert second_review.json()["revision_id"] != first_review["revision_id"]
    assert {item["status"] for item in second_review.json()["findings"]} == {"supported"}
    client.post(f"/api/submissions/{submission_id}/submit", headers=headers())
    approved = client.post(f"/api/submissions/{submission_id}/decisions", headers=headers("dana@meridianlabs.example"), json={"decision": "approved", "comments": "Aligned to the current ledger."})
    assert approved.status_code == 200
    assert approved.json()["revision_id"] == second_review.json()["revision_id"]
    assert client.post(f"/api/submissions/{submission_id}/revisions", headers=headers(), json={"content": "Changed after approval."}).status_code == 409


def test_missing_evidence_is_unverified_not_contradicted(client):
    _, review = create_and_review(client, "MeridianPay is guaranteed to be the best service for everyone.")
    assert any(item["status"] == "unverified" for item in review["findings"])
    policy = next(item for item in review["findings"] if item["status"] == "policy_violation")
    assert policy["policy_citation"] is not None, policy
    assert policy["policy_citation"]["version"] == 1
    assert all(item["evidence"] is None for item in review["findings"])


def test_approving_a_material_finding_requires_override_justification(client):
    submission_id, _ = create_and_review(client)
    client.post(f"/api/submissions/{submission_id}/submit", headers=headers())
    response = client.post(f"/api/submissions/{submission_id}/decisions", headers=headers("dana@meridianlabs.example"), json={"decision": "approved", "comments": "Ship it"})
    assert response.status_code == 422
    justified = client.post(f"/api/submissions/{submission_id}/decisions", headers=headers("dana@meridianlabs.example"), json={"decision": "approved", "override_justification": "Legal reviewed the campaign exception."})
    assert justified.status_code == 200


def test_new_fact_version_supersedes_old_version_and_drives_review(client):
    updated = client.post("/api/knowledge/facts", headers=headers("morgan@meridianlabs.example"), json={
        "fact_key": "fee", "label": "Transfer fee", "claim_text": "International transfers are subject to a 2% processing fee.",
        "source_name": "Commercial Pricing Policy", "source_version": "v4.0", "owner": "Finance",
    })
    assert updated.status_code == 201
    assert updated.json()["version"] == 2
    records = client.get("/api/knowledge/facts", headers=headers()).json()
    assert {fact["approval_status"] for fact in records if fact["fact_key"] == "fee"} == {"approved", "superseded"}

    submission, review = create_and_review(client, "MeridianPay charges a 1.5% processing fee.")
    fee = next(item for item in review["findings"] if item["claim_text"] == "1.5% processing fee")
    assert fee["status"] == "contradicted"
    assert fee["evidence"]["fact_version"] == 2
    assert "2% processing fee" in fee["suggestion"]["text"]
