from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import jwt
from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models import Membership, Organization, User

security = HTTPBearer(auto_error=False)


@dataclass
class Actor:
    user: User
    organization: Organization
    role: str


def create_access_token(user_id: str, email: str, organization_slug: str, role: str, expires_delta: timedelta | None = None) -> str:
    """Create a signed OIDC/JWT bearer token for authenticated API requests."""
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=24))
    payload = {
        "sub": user_id,
        "email": email.lower(),
        "org": organization_slug,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "iss": "proofgate-auth",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def get_current_actor(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    x_demo_user: str | None = Header(default=None),
    x_organization: str = Header(default="meridian-labs"),
    db: Session = Depends(get_db),
) -> Actor:
    """
    Secure Production Identity Resolver:
    1. If a valid Authorization: Bearer <jwt> is presented, verify and decode it.
    2. Fallback to X-Demo-User header ONLY IF settings.demo_mode is explicitly true.
    3. Fail closed if unauthenticated, invalid token, or expired token.
    4. Server-side tenant boundary check: verifies user is an active member of organization.
    """
    user_email = None
    org_slug = x_organization

    # 1. Bearer Token Verification (OIDC/JWT)
    if credentials and credentials.credentials:
        try:
            payload = jwt.decode(
                credentials.credentials,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
                options={"verify_exp": True},
            )
            user_email = payload.get("email")
            if "org" in payload:
                org_slug = payload["org"]
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired. Please log in again.")
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="Invalid authorization token.")

    # 2. Demo Mode Fallback (local development only)
    elif settings.demo_mode:
        if not x_demo_user:
            raise HTTPException(status_code=401, detail="Authentication required. Provide a bearer token or select a demo user.")
        user_email = x_demo_user.lower()
    else:
        raise HTTPException(
            status_code=401,
            detail="Production authentication required. Provide a valid Authorization: Bearer <token> header.",
        )

    # 3. Database & Tenant Membership Verification
    user = db.query(User).filter(User.email == user_email).first()
    organization = db.query(Organization).filter(Organization.slug == org_slug).first()

    if user is None or organization is None:
        raise HTTPException(status_code=401, detail="Authenticated user or organization not found in tenant registry.")

    membership = db.query(Membership).filter(
        Membership.user_id == user.id,
        Membership.organization_id == organization.id,
        Membership.active.is_(True),
    ).first()

    if membership is None:
        raise HTTPException(status_code=403, detail="Forbidden: User is not an active member of this organization tenant.")

    return Actor(user=user, organization=organization, role=membership.role)


def require_roles(*roles: str):
    def check(actor: Actor = Depends(get_current_actor)) -> Actor:
        if actor.role not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: Role '{actor.role}' cannot perform this action. Required: {', '.join(roles)}",
            )
        return actor
    return check
