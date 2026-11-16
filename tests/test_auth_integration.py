"""Optional live Firebase integration tests.

These are intentionally separate from mocked Firebase tests and are skipped
unless both FIREBASE_SERVICE_ACCOUNT_JSON and FIREBASE_ID_TOKEN are supplied.
No credentials are stored in the repository.
"""

import os

import pytest

from backend.auth import get_current_user
from fastapi.security import HTTPAuthorizationCredentials


pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    not (
        os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        and os.getenv("FIREBASE_ID_TOKEN")
    ),
    reason="Live Firebase credentials are not configured",
)
def test_live_firebase_id_token_verification():
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=os.environ["FIREBASE_ID_TOKEN"],
    )

    claims = get_current_user(credentials)

    assert claims["uid"]
