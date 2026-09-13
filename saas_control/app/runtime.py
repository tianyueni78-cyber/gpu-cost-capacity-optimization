import os
from datetime import datetime, timedelta, timezone

import jwt

from .main import create_app
from .store import from_environment


_SECRET = os.environ["LOCAL_JWT_SECRET"]
_ALGORITHM = "HS256"


def issue_token(user_id: str, organization_id: str | None = None, project_id: str | None = None):
    claims = {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(hours=8)}
    if organization_id and project_id:
        claims.update({
            "organization_id": organization_id,
            "project_id": project_id,
            "role": "ORG_ADMIN",
            "subscription_active": True,
        })
    return jwt.encode(claims, _SECRET, algorithm=_ALGORITHM)


def decode_token(token: str):
    return jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])


app = create_app(
    decode_token,
    store=from_environment(),
    issue_token=issue_token,
    dev_credentials=(
        os.environ["LOCAL_DEV_EMAIL"],
        os.environ["LOCAL_DEV_PASSWORD"],
        os.environ["LOCAL_DEV_USER_ID"],
    ),
)
