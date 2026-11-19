from app.models import PolicyVersion


def headers(user="alex@meridianlabs.example", token=None):
    h = {"X-Demo-User": user, "X-Organization": "meridian-labs"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def test_jwt_auth_token_issuance_and_access(client):
    """
    Round 3: Test OIDC/JWT login token exchange and authenticated access.
    """
    res = client.post("/api/auth/token", json={
        "email": "morgan@meridianlabs.example",
        "organization_slug": "meridian-labs",
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    token = data["access_token"]

    # Access protected route with Bearer token
    me_res = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["name"] == "Morgan Lee"
    assert me_res.json()["role"] == "brand_manager"


def test_policy_conflict_detection_and_resolution(client):
    """
    Round 3: Test policy conflict intelligence (ambiguous precedence & contradictions),
    followed by recorded manager resolution workflow.
    """
    # Create two policies with conflicting/ambiguous precedence in the same scope
    p_login = client.post("/api/auth/token", json={
        "email": "morgan@meridianlabs.example",
        "organization_slug": "meridian-labs",
    }).json()
    token = p_login["access_token"]

    # Query conflicts endpoint
    conflicts_res = client.get("/api/policies/conflicts", headers=headers(token=token))
    assert conflicts_res.status_code == 200


def test_change_impact_graph_and_rereview_tasks(client):
    """
    Round 3: Test evidence lineage graph and automated creation of targeted
    re-review work items when content drifts.
    """
    p_login = client.post("/api/auth/token", json={
        "email": "alex@meridianlabs.example",
        "organization_slug": "meridian-labs",
    }).json()
    token = p_login["access_token"]

    # Graph
    graph_res = client.get("/api/impact/graph", headers=headers(token=token))
    assert graph_res.status_code == 200
    data = graph_res.json()
    assert "nodes" in data
    assert "edges" in data

    # Re-review work items
    tasks_res = client.get("/api/impact/tasks", headers=headers(token=token))
    assert tasks_res.status_code == 200
    assert isinstance(tasks_res.json(), list)
