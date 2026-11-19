
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend import main
from backend.database import Base, get_db
from backend import models  # Ensure all models are registered with Base


@pytest.fixture(autouse=True)
def test_database(monkeypatch):
    """Provide a fresh isolated SQLite database for each test."""
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )

    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[get_db] = override_get_db
    main.app.dependency_overrides[main.get_current_user] = lambda: {
        "uid": "pytest-user",
        "email": "pytest@example.com",
    }

    try:
        yield
    finally:
        main.app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()
