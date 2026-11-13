import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db import Base, get_db
from app.main import app
from app.models import ApprovedFact, BrandPolicy, EvidenceSource, Membership, Organization, PolicyVersion, User


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True)
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    with TestingSession() as db:
        org = Organization(id="org-1", name="Meridian Labs", slug="meridian-labs")
        db.add(org)
        creator = User(id="user-creator", email="alex@meridianlabs.example", display_name="Alex Rivera")
        reviewer = User(id="user-reviewer", email="dana@meridianlabs.example", display_name="Dana Kim")
        manager = User(id="user-manager", email="morgan@meridianlabs.example", display_name="Morgan Lee")
        db.add_all([creator, reviewer, manager])
        db.flush()
        db.add_all([
            Membership(organization_id=org.id, user_id=creator.id, role="creator"),
            Membership(organization_id=org.id, user_id=reviewer.id, role="reviewer"),
            Membership(organization_id=org.id, user_id=manager.id, role="brand_manager"),
        ])
        facts = [
            ("fee", "Transfer fee", "International transfers are subject to a 1.5% processing fee."),
            ("settlement", "Settlement time", "Transfers settle in 1–2 business days."),
            ("markets", "Supported markets", "MeridianPay is available in 85 supported markets."),
        ]
        for key, label, text in facts:
            source = EvidenceSource(organization_id=org.id, name=f"{label} source", source_version="v1.0", owner="Finance", approval_status="approved")
            db.add(source)
            db.flush()
            db.add(ApprovedFact(organization_id=org.id, source_id=source.id, fact_key=key, version=1, label=label, claim_text=text, owner="Finance", approval_status="approved"))
        policy = BrandPolicy(organization_id=org.id, name="Product claims", status="active")
        db.add(policy)
        db.flush()
        db.add(PolicyVersion(organization_id=org.id, policy_id=policy.id, version=1, rule_text="Claims must match current approved facts. Unsupported promotional guarantees must not be published.", approval_status="approved"))
        db.commit()

    def override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def headers(user="alex@meridianlabs.example", organization="meridian-labs"):
    return {"X-Demo-User": user, "X-Organization": organization}
