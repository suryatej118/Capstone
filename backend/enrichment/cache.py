import os
import sqlite3
import time

from dotenv import load_dotenv

load_dotenv()


CACHE_DB_PATH = os.getenv(
    "CACHE_DB_PATH",
    "./data/company_cache.db",
)

CACHE_TTL_SECONDS = 7 * 24 * 60 * 60


def _get_connection():
    directory = os.path.dirname(CACHE_DB_PATH)

    if directory:
        os.makedirs(directory, exist_ok=True)

    return sqlite3.connect(CACHE_DB_PATH)


def initialize_cache() -> None:
    """
    Create the company cache table if it does not already exist.
    """

    with _get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS company_cache (
                company_name TEXT PRIMARY KEY,
                response_json TEXT NOT NULL,
                cached_at REAL NOT NULL
            )
            """
        )

        connection.commit()


def get_cached_result(company_name: str):
    """
    Return a cached OpenCorporates result if it is still valid.
    """

    initialize_cache()

    with _get_connection() as connection:
        row = connection.execute(
            """
            SELECT response_json, cached_at
            FROM company_cache
            WHERE company_name = ?
            """,
            (company_name,),
        ).fetchone()

    if row is None:
        return None

    response_json, cached_at = row

    if time.time() - cached_at > CACHE_TTL_SECONDS:
        return None

    return response_json


def save_cached_result(
    company_name: str,
    response_json: str,
) -> None:
    """
    Save an OpenCorporates result to the local cache.
    """

    initialize_cache()

    with _get_connection() as connection:
        connection.execute(
            """
            INSERT INTO company_cache (
                company_name,
                response_json,
                cached_at
            )
            VALUES (?, ?, ?)
            ON CONFLICT(company_name)
            DO UPDATE SET
                response_json = excluded.response_json,
                cached_at = excluded.cached_at
            """,
            (
                company_name,
                response_json,
                time.time(),
            ),
        )

        connection.commit()