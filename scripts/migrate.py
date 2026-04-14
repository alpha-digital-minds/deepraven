#!/usr/bin/env python3
"""
DeepRaven migration runner.

Usage:
    python scripts/migrate.py supabase/migrations/002_whatever.sql
    python scripts/migrate.py                     # runs all pending migrations in order

Migrations are tracked in the `schema_migrations` table (created on first run).
A migration file is skipped if it has already been applied.
"""
import asyncio
import hashlib
import re
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

import os

SUPABASE_URL = os.environ["SUPABASE_URL"]
MANAGEMENT_TOKEN = os.environ["SUPABASE_MANAGEMENT_TOKEN"]

# Extract project ref from URL: https://<ref>.supabase.co
_ref_match = re.search(r"https://([^.]+)\.supabase\.co", SUPABASE_URL)
if not _ref_match:
    sys.exit(f"Cannot parse project ref from SUPABASE_URL: {SUPABASE_URL}")
PROJECT_REF = _ref_match.group(1)

API_URL = f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/query"
MIGRATIONS_DIR = Path(__file__).parent.parent / "supabase" / "migrations"

TRACKING_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
  filename   text PRIMARY KEY,
  applied_at timestamptz DEFAULT now()
);
"""


async def execute_sql(client: httpx.AsyncClient, sql: str) -> dict:
    resp = await client.post(
        API_URL,
        headers={"Authorization": f"Bearer {MANAGEMENT_TOKEN}", "Content-Type": "application/json"},
        json={"query": sql},
        timeout=30,
    )
    if resp.status_code not in (200, 201):
        sys.exit(f"SQL execution failed ({resp.status_code}): {resp.text}")
    return resp.json()


async def get_applied(client: httpx.AsyncClient) -> set[str]:
    result = await execute_sql(client, "SELECT filename FROM schema_migrations;")
    return {row["filename"] for row in (result if isinstance(result, list) else [])}


async def apply(client: httpx.AsyncClient, path: Path) -> None:
    sql = path.read_text()
    print(f"  Applying {path.name}...", end=" ", flush=True)
    await execute_sql(client, sql)
    await execute_sql(
        client,
        f"INSERT INTO schema_migrations(filename) VALUES ('{path.name}') ON CONFLICT DO NOTHING;",
    )
    print("done.")


async def main(targets: list[Path]) -> None:
    async with httpx.AsyncClient() as client:
        # Ensure tracking table exists
        await execute_sql(client, TRACKING_TABLE_SQL)
        applied = await get_applied(client)

        pending = [p for p in targets if p.name not in applied]
        if not pending:
            print("Nothing to migrate — all files already applied.")
            return

        print(f"Running {len(pending)} migration(s):")
        for path in pending:
            await apply(client, path)

        print("Migration complete.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Explicit file(s) provided
        targets = [Path(f) for f in sys.argv[1:]]
        for t in targets:
            if not t.exists():
                sys.exit(f"File not found: {t}")
    else:
        # Run all migrations in sorted order
        targets = sorted(MIGRATIONS_DIR.glob("*.sql"))
        if not targets:
            sys.exit(f"No .sql files found in {MIGRATIONS_DIR}")

    asyncio.run(main(targets))
