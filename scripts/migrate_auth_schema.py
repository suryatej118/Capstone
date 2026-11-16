"""Safely add authentication ownership tables and scan ownership support."""

from sqlalchemy import inspect, text

from backend.database import Base, engine
from backend.models import Scan, User


def main() -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    if "users" not in tables:
        User.__table__.create(bind=engine, checkfirst=True)

    scan_columns = {
        column["name"] for column in inspect(engine).get_columns("scans")
    }

    if "user_id" not in scan_columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE scans ADD COLUMN user_id INTEGER")
            )

    inspector = inspect(engine)
    indexes = {index["name"] for index in inspector.get_indexes("scans")}
    if "ix_scans_user_id" not in indexes:
        with engine.begin() as connection:
            connection.execute(
                text("CREATE INDEX ix_scans_user_id ON scans (user_id)")
            )

    print(
        "Authentication schema is ready. Existing scans remain unassigned "
        "and will not be visible to authenticated users."
    )


if __name__ == "__main__":
    main()
