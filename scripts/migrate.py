#!/usr/bin/env python3
"""Run SQL migrations against Supabase PostgreSQL in order."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
MIGRATIONS_DIR = ROOT / "backend" / "migrations" / "versions"


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for env_file in (ROOT / ".env", ROOT / ".env.local"):
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return env


def get_db_url(env: dict[str, str]) -> str:
    url = os.getenv("DATABASE_URL") or env.get("DATABASE_URL")
    if url:
        return url

    print("ERROR: DATABASE_URL is not set in .env\n")
    print("Add this line to your .env file:")
    print('  DATABASE_URL=postgresql://postgres.[ref]:[password]@db.[ref].supabase.co:5432/postgres')
    print()
    print("Find it at: Supabase Dashboard → Settings → Database → Connection string → URI")
    print("  (use the direct connection, not the pooler)")
    sys.exit(1)


def ensure_psycopg2() -> None:
    try:
        import psycopg2  # noqa: F401
    except ImportError:
        print("psycopg2 not found — installing psycopg2-binary...")
        import subprocess
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "psycopg2-binary", "--quiet"],
            check=True,
        )
        print("Installed.\n")


def run_migrations() -> None:
    ensure_psycopg2()
    import psycopg2

    env = load_env()
    db_url = get_db_url(env)

    sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not sql_files:
        print("No migration files found in", MIGRATIONS_DIR)
        return

    print(f"Connecting to database...")
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()
    except Exception as e:
        print(f"ERROR: Could not connect — {e}")
        sys.exit(1)

    print(f"Running {len(sql_files)} migration(s):\n")

    errors: list[tuple[str, str]] = []
    for sql_file in sql_files:
        print(f"  {sql_file.name} ...", end=" ", flush=True)
        try:
            cur.execute(sql_file.read_text())
            print("OK")
        except Exception as e:
            short = str(e).splitlines()[0]
            print(f"FAILED — {short}")
            errors.append((sql_file.name, str(e)))

    cur.close()
    conn.close()

    print()
    if errors:
        print(f"{len(errors)} migration(s) failed:")
        for name, err in errors:
            print(f"  {name}: {err}")
        sys.exit(1)
    else:
        print(f"All {len(sql_files)} migrations applied successfully.")


if __name__ == "__main__":
    run_migrations()
