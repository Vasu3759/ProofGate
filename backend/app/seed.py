from datetime import datetime, timezone

from app.db import SessionLocal
from app.models import ApprovedFact, BrandPolicy, EvidenceSource, Membership, Organization, PolicyVersion, User

ORG_ID = "00000000-0000-4000-8000-000000000001"
DEMO_USERS = [
    ("alex@meridianlabs.example", "Alex Rivera", "creator"),
    ("dana@meridianlabs.example", "Dana Kim", "reviewer"),
    ("morgan@meridianlabs.example", "Morgan Lee", "brand_manager"),
]
FACTS = [
    ("fee", "Transfer fee", "International transfers are subject to a 1.5% processing fee.", "Commercial Pricing Policy", "v3.2"),
    ("settlement", "Settlement time", "Transfers settle in 1–2 business days.", "Product Operations Guide", "v2.4"),
    ("markets", "Supported markets", "MeridianPay is available in 85 supported markets.", "Market Availability Register", "v1.8"),
]


def seed():
    db = SessionLocal()
    try:
        organization = db.query(Organization).filter(Organization.slug == "meridian-labs").first()
        if organization:
            return
        org = Organization(id=ORG_ID, name="Meridian Labs", slug="meridian-labs")
        db.add(org)
        users = {}
        for email, name, role in DEMO_USERS:
            user = User(email=email, display_name=name)
            db.add(user)
            db.flush()
            users[role] = user
            db.add(Membership(organization_id=ORG_ID, user_id=user.id, role=role, active=True))
        manager = users["brand_manager"]
        for key, label, claim, source_name, version in FACTS:
            source = EvidenceSource(organization_id=ORG_ID, name=source_name, source_version=version, owner="Finance & Commercial Operations", approval_status="approved", effective_at=datetime(2026, 11, 6, tzinfo=timezone.utc))
            db.add(source)
            db.flush()
            db.add(ApprovedFact(organization_id=ORG_ID, source_id=source.id, fact_key=key, version=1, label=label, claim_text=claim, owner="Finance & Commercial Operations", approval_status="approved", effective_at=datetime(2026, 11, 6, tzinfo=timezone.utc)))
        policy = BrandPolicy(organization_id=ORG_ID, name="External product claims", status="active")
        db.add(policy)
        db.flush()
        db.add(PolicyVersion(organization_id=ORG_ID, policy_id=policy.id, version=1, rule_text="External product facts must match current approved records. Unsupported guarantees must not be published.", approval_status="approved", effective_at=datetime(2026, 11, 6, tzinfo=timezone.utc)))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
