#!/usr/bin/env python3
"""Create/refresh the read-only Postgres role Grafana uses (`grafana_ro`).

Runs INSIDE the auth-service pod, which already holds DATABASE_URL and SQLAlchemy:

    kubectl exec -i -n textara deploy/auth-service -- python -u - "$GRAFANA_DB_PASSWORD" < scripts/grafana_db_role.py

Idempotent. The role can SELECT only non-PII columns of `users` plus `usage_daily`,
every transaction is forced read-only, and the password is rotated on each run
(so rotating the GH secret and re-running is all it takes).
"""

import os
import sys

from sqlalchemy import create_engine, text

ROLE = "grafana_ro"
USERS_COLUMNS = {"id", "plan", "created_at", "email_verified"}

if len(sys.argv) != 2 or not sys.argv[1]:
    print("usage: grafana_db_role.py <password>", file=sys.stderr)
    sys.exit(2)
password = sys.argv[1]

engine = create_engine(os.environ["DATABASE_URL"])

STATEMENTS = [
    # create the role once
    f"""
    DO $$ BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{ROLE}') THEN
        CREATE ROLE {ROLE} LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
      END IF;
    END $$
    """,
    # password via a bound parameter + format(%L): no quoting risk, rotates every run
    "SELECT set_config('textara.grafana_pw', :pw, true)",
    f"""
    DO $$ BEGIN
      EXECUTE format('ALTER ROLE {ROLE} LOGIN PASSWORD %L CONNECTION LIMIT 5',
                     current_setting('textara.grafana_pw'));
      EXECUTE format('GRANT CONNECT ON DATABASE %I TO {ROLE}', current_database());
    END $$
    """,
    f"GRANT USAGE ON SCHEMA public TO {ROLE}",
    # reset so the column list below is authoritative, then grant only non-PII columns
    f"REVOKE ALL ON public.users FROM {ROLE}",
    f"GRANT SELECT ({', '.join(sorted(USERS_COLUMNS))}) ON public.users TO {ROLE}",
    f"GRANT SELECT ON public.usage_daily TO {ROLE}",
    f"ALTER ROLE {ROLE} SET default_transaction_read_only = on",
    f"ALTER ROLE {ROLE} SET statement_timeout = '15s'",
]

with engine.begin() as conn:
    for stmt in STATEMENTS:
        conn.execute(text(stmt), {"pw": password} if ":pw" in stmt else {})

# Self-check: the effective column privileges must be exactly the intended set.
with engine.connect() as conn:
    cols = {
        r[0]
        for r in conn.execute(
            text(
                "SELECT column_name FROM information_schema.column_privileges "
                "WHERE grantee = :r AND table_schema = 'public' AND table_name = 'users' "
                "AND privilege_type = 'SELECT'"
            ),
            {"r": ROLE},
        )
    }
    tables = {
        r[0]
        for r in conn.execute(
            text(
                "SELECT table_name FROM information_schema.role_table_grants "
                "WHERE grantee = :r AND table_schema = 'public' AND privilege_type = 'SELECT'"
            ),
            {"r": ROLE},
        )
    }

print(f"{ROLE}: users columns = {sorted(cols)}; table grants = {sorted(tables)}")
if cols != USERS_COLUMNS:
    print(f"ERROR: expected users columns {sorted(USERS_COLUMNS)}", file=sys.stderr)
    sys.exit(1)
if "usage_daily" not in tables:
    print("ERROR: usage_daily not granted", file=sys.stderr)
    sys.exit(1)
print("grafana_ro ready")
