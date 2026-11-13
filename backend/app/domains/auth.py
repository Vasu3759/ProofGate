from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models import Membership, Organization, User


@dataclass
class Actor:
    user: User
    organization: Organization
    role: str


def get_current_actor(
    x_demo_user: str | None = Header(default=None),
    x_organization: str = Header(default="meridian-labs"),
    db: Session = Depends(get_db),
) -> Actor:
    if not settings.demo_mode:
        raise HTTPException(status_code=401, detail="Authentication is not configured. Enable demo mode only for local development.")
    if not x_demo_user:
        raise HTTPException(status_code=401, detail="Choose a demo user to continue.")
    user = db.query(User).filter(User.email == x_demo_user.lower()).first()
    organization = db.query(Organization).filter(Organization.slug == x_organization).first()
    if user is None or organization is None:
        raise HTTPException(status_code=401, detail="Demo user or organization was not found. Seed the demo workspace first.")
    membership = db.query(Membership).filter(
        Membership.user_id == user.id,
        Membership.organization_id == organization.id,
        Membership.active.is_(True),
    ).first()
    if membership is None:
        raise HTTPException(status_code=403, detail="This user is not a member of the selected organization.")
    return Actor(user=user, organization=organization, role=membership.role)


def require_roles(*roles: str):
    def check(actor: Actor = Depends(get_current_actor)) -> Actor:
        if actor.role not in roles:
            raise HTTPException(status_code=403, detail="Your role cannot perform this action.")
        return actor
    return check
