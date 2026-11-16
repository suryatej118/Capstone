import json
import os
from functools import lru_cache

import firebase_admin
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials
from firebase_admin import exceptions as firebase_exceptions

bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def get_firebase_app():
    if firebase_admin._apps:
        return firebase_admin.get_app()

    raw_credentials = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if not raw_credentials:
        raise RuntimeError(
            "FIREBASE_SERVICE_ACCOUNT_JSON is required for Firebase Admin authentication."
        )

    try:
        service_account = json.loads(raw_credentials)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "FIREBASE_SERVICE_ACCOUNT_JSON must contain valid JSON."
        ) from exc

    return firebase_admin.initialize_app(
        credentials.Certificate(service_account),
        {"projectId": os.getenv("FIREBASE_PROJECT_ID") or service_account.get("project_id")},
    )


def get_current_user(
    credentials_header: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
) -> dict:
    if credentials_header is None or credentials_header.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer authentication is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        get_firebase_app()
        return firebase_auth.verify_id_token(credentials_header.credentials)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is not configured.",
        ) from exc
    except (firebase_exceptions.FirebaseError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
