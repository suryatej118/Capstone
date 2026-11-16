"""Safely add authentication ownership tables and scan ownership support.

The migration is additive and preserves every existing scan row. Legacy scans
remain NULL-owned and are intentionally not assigned to a Firebase user.
"""

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    inspect,
    text,
)

from backend.database import engine
from backend.models import Scan, User


USER_ID_INDEX = "ix_scans_user_id"
USER_FK_NAME = "fk_scans_user_id_users"


def _create_users() -> None:
    if "users" not in inspect(engine).get_table_names():
        User.__table__.create(bind=engine, checkfirst=True)


def _add_postgres_ownership() -> None:
    inspector = inspect(engine)
    scan_columns = {
        column["name"] for column in inspector.get_columns("scans")
    }

    with engine.begin() as connection:
        if "user_id" not in scan_columns:
            connection.execute(
                text("ALTER TABLE scans ADD COLUMN user_id INTEGER")
            )

        foreign_keys = inspector.get_foreign_keys("scans")
        has_user_fk = any(
            foreign_key.get("name") == USER_FK_NAME
            or (
                foreign_key.get("referred_table") == "users"
                and foreign_key.get("constrained_columns") == ["user_id"]
            )
            for foreign_key in foreign_keys
        )
        if not has_user_fk:
            connection.execute(
                text(
                    "ALTER TABLE scans ADD CONSTRAINT "
                    f"{USER_FK_NAME} FOREIGN KEY (user_id) REFERENCES users (id)"
                )
            )

        indexes = {
            index["name"] for index in inspect(connection).get_indexes("scans")
        }
        if USER_ID_INDEX not in indexes:
            connection.execute(
                text("CREATE INDEX ix_scans_user_id ON scans (user_id)")
            )


def _sqlite_scan_table_with_fk() -> Table:
    metadata = MetaData()
    Table(
        "users",
        metadata,
        Column("id", Integer, primary_key=True),
    )
    return Table(
        "scans_auth_migration",
        metadata,
        Column("id", Integer, primary_key=True, index=True),
        Column("requester_id", String(255), nullable=True, index=True),
        Column("user_id", Integer, ForeignKey("users.id"), nullable=True, index=True),
        Column("platform", String(100), nullable=True),
        Column("submitted_text", Scan.submitted_text.type, nullable=False),
        Column("rule_score", Integer, nullable=False),
        Column("ml_probability", Scan.ml_probability.type, nullable=True),
        Column("final_score", Scan.final_score.type, nullable=False),
        Column("risk_level", String(30), nullable=False, index=True),
        Column("confidence", Integer, nullable=False),
        Column("hiring_intent_score", Integer, nullable=False),
        Column("reasons", Scan.reasons.type, nullable=False),
        Column("highlighted_spans", Scan.highlighted_spans.type, nullable=False),
        Column("hiring_intent_reasons", Scan.hiring_intent_reasons.type, nullable=False),
        Column("suggested_templates", Scan.suggested_templates.type, nullable=False),
        Column("created_at", Scan.created_at.type, nullable=False),
    )


def _add_sqlite_ownership() -> None:
    inspector = inspect(engine)
    scan_columns = {
        column["name"] for column in inspector.get_columns("scans")
    }
    foreign_keys = inspector.get_foreign_keys("scans")
    has_user_fk = any(
        foreign_key.get("referred_table") == "users"
        and foreign_key.get("constrained_columns") == ["user_id"]
        for foreign_key in foreign_keys
    )

    if "user_id" in scan_columns and has_user_fk:
        return

    migrated_table = _sqlite_scan_table_with_fk()
    columns = [
        "id",
        "requester_id",
        "platform",
        "submitted_text",
        "rule_score",
        "ml_probability",
        "final_score",
        "risk_level",
        "confidence",
        "hiring_intent_score",
        "reasons",
        "highlighted_spans",
        "hiring_intent_reasons",
        "suggested_templates",
        "created_at",
    ]
    if "user_id" in scan_columns:
        columns.insert(2, "user_id")

    with engine.begin() as connection:
        connection.execute(text("PRAGMA foreign_keys=OFF"))
        migrated_table.create(connection)
        column_sql = ", ".join(columns)
        connection.execute(
            text(
                f"INSERT INTO scans_auth_migration ({column_sql}) "
                f"SELECT {column_sql} FROM scans"
            )
        )
        connection.execute(text("DROP TABLE scans"))
        connection.execute(text("ALTER TABLE scans_auth_migration RENAME TO scans"))
        connection.execute(text("PRAGMA foreign_keys=ON"))

    # Recreate the application-facing indexes after the table replacement.
    Scan.__table__.metadata.create_all(bind=engine, checkfirst=True)


def main() -> None:
    _create_users()
    if "scans" not in inspect(engine).get_table_names():
        Scan.__table__.create(bind=engine, checkfirst=True)

    if engine.dialect.name == "postgresql":
        _add_postgres_ownership()
    elif engine.dialect.name == "sqlite":
        _add_sqlite_ownership()
    else:
        raise RuntimeError(
            f"Unsupported database dialect: {engine.dialect.name}"
        )

    print(
        "Authentication schema is ready. Existing scans remain unassigned "
        "and will not be visible to authenticated users."
    )


if __name__ == "__main__":
    main()
