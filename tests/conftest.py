import pytest

from backend import main


@pytest.fixture(autouse=True)
def authenticated_test_user():
    """Keep legacy endpoint tests authenticated without using real Firebase."""
    main.app.dependency_overrides[main.get_current_user] = lambda: {
        "uid": "pytest-user",
        "email": "pytest@example.com",
    }
    yield
    main.app.dependency_overrides.clear()
