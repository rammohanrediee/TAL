"""Verify a local PostgreSQL login and save TAL's connection URL privately."""

import os
import tempfile
from getpass import getpass
from pathlib import Path

import psycopg
from sqlalchemy.engine import URL


def main() -> int:
    username = input("Local PostgreSQL username [postgres]: ").strip() or "postgres"
    database = input("TAL database name [tal]: ").strip() or "tal"
    password = getpass("Local PostgreSQL password (hidden): ")
    if not password:
        print("No password entered; .env was not changed.")
        return 1

    try:
        with (
            psycopg.connect(
                host="localhost",
                port=5432,
                user=username,
                password=password,
                dbname=database,
                connect_timeout=5,
            ) as connection,
            connection.cursor() as cursor,
        ):
            cursor.execute(
                "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"
            )
            table_count = cursor.fetchone()[0]
    except psycopg.Error as error:
        print(f"Database connection failed: {error}")
        print(".env was not changed.")
        return 1

    url = URL.create(
        "postgresql+asyncpg",
        username=username,
        password=password,
        host="localhost",
        port=5432,
        database=database,
    ).render_as_string(hide_password=False)
    env_path = Path(__file__).resolve().parents[1] / ".env"
    lines = env_path.read_text().splitlines()
    replacements = {
        "DATABASE_URL": url,
        "DATABASE_URL_UNPOOLED": url,
    }
    updated = [
        f"{key}={replacements[key]}" if (key := line.split("=", 1)[0]) in replacements else line
        for line in lines
    ]
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=env_path.parent, prefix=".env.tmp.", delete=False
    ) as temporary:
        temporary.write("\n".join(updated) + "\n")
        temporary_path = Path(temporary.name)
    try:
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, env_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    print(
        f"Connected to local database '{database}' as '{username}' ({table_count} public tables)."
    )
    print("Saved local database connection to .env with owner-only permissions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
