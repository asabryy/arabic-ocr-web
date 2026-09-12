#!/usr/bin/env python3
"""Provision Grafana from this repo: the read-only Postgres datasource and every
dashboard under monitoring/grafana/dashboards/. Idempotent; safe to re-run.

The monitoring stack itself lives outside this repo and its dashboards are
file-provisioned, so ours are created through the HTTP API (into the same
"Textara" folder) and re-applied on every deploy — Grafana's state is a local
sqlite file, so this keeps the dashboard alive even across a pod rebuild.

Stdlib only, so it runs on a bare CI runner.

Env:
  GRAFANA_URL             default https://grafana.textara.app
  GRAFANA_ADMIN_USER      default admin
  GRAFANA_ADMIN_PASSWORD  required (unless --validate)
  AUTH_DATABASE_URL       required (unless --validate/--dashboards-only): host/port/db parsed from it
  GRAFANA_DB_PASSWORD     required (unless --validate/--dashboards-only)
  GRAFANA_DB_USER         default grafana_ro
  GRAFANA_DB_PORT         optional override (e.g. 5432 to force session mode on a Supabase pooler)
  GRAFANA_DB_SSLMODE      optional override
  GRAFANA_FOLDER_UID      default dfg912x104zcwe (existing "Textara" folder)
  GITHUB_SHA              used in the dashboard version message

Flags:
  --validate         offline: parse the JSON files and check their shape, then exit
  --dashboards-only  skip the datasource (useful before the DB role exists)
"""

import argparse
import base64
import glob
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD_DIR = os.path.join(ROOT, "monitoring", "grafana", "dashboards")
DATASOURCE_FILE = os.path.join(ROOT, "monitoring", "grafana", "datasources", "textara-db.json")
DATASOURCE_UID = "textara-db"


def die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


# ── Offline validation ────────────────────────────────────────────────────────

def validate() -> list[dict]:
    dashboards = []
    for path in sorted(glob.glob(os.path.join(DASHBOARD_DIR, "*.json"))):
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        for key in ("uid", "title", "panels"):
            if key not in d:
                die(f"{path}: missing '{key}'")
        if d.get("id") is not None:
            die(f"{path}: 'id' must be null (Grafana assigns it)")
        dashboards.append(d)
        print(f"  ok  {os.path.basename(path)}  uid={d['uid']}  panels={len(d['panels'])}")
    if not dashboards:
        die("no dashboards found")
    with open(DATASOURCE_FILE, encoding="utf-8") as f:
        ds = json.load(f)
    if ds.get("uid") != DATASOURCE_UID:
        die(f"{DATASOURCE_FILE}: uid must be {DATASOURCE_UID}")
    print(f"  ok  datasource {ds['name']}")
    return dashboards


# ── Grafana HTTP ──────────────────────────────────────────────────────────────

class Grafana:
    def __init__(self, url: str, user: str, password: str):
        self.url = url.rstrip("/")
        token = base64.b64encode(f"{user}:{password}".encode()).decode()
        self.headers = {"Authorization": f"Basic {token}", "Content-Type": "application/json"}

    def req(self, method: str, path: str, body=None):
        data = json.dumps(body).encode() if body is not None else None
        r = urllib.request.Request(self.url + path, data=data, method=method, headers=self.headers)
        try:
            with urllib.request.urlopen(r, timeout=30) as resp:
                raw = resp.read().decode()
                return resp.status, (json.loads(raw) if raw else {})
        except urllib.error.HTTPError as e:
            raw = e.read().decode()
            try:
                return e.code, json.loads(raw)
            except ValueError:
                return e.code, {"message": raw}


# ── Datasource ────────────────────────────────────────────────────────────────

def db_settings_from_url(url: str) -> dict:
    u = urllib.parse.urlsplit(url)
    if not u.scheme.startswith(("postgres", "postgresql")):
        die(f"unsupported DB URL scheme: {u.scheme}")
    host = u.hostname or die("DB URL has no host")
    port = int(os.environ.get("GRAFANA_DB_PORT") or u.port or 5432)
    database = (u.path or "/").lstrip("/").split("?")[0] or "postgres"
    qs = urllib.parse.parse_qs(u.query)
    internal = host.endswith((".svc", ".cluster.local")) or host in ("postgres", "localhost")
    sslmode = os.environ.get("GRAFANA_DB_SSLMODE") or qs.get("sslmode", ["disable" if internal else "require"])[0]
    user = os.environ.get("GRAFANA_DB_USER", "grafana_ro")
    # Supavisor (Supabase pooler) routes on the "<user>.<project-ref>" login suffix.
    if host.endswith("pooler.supabase.com") and u.username:
        m = re.match(r"^[^.]+\.(?P<ref>[a-z0-9]+)$", u.username)
        if m:
            user = f"{user}.{m.group('ref')}"
    return {"host": host, "port": port, "database": database, "user": user, "sslmode": sslmode}


def upsert_datasource(g: Grafana) -> None:
    with open(DATASOURCE_FILE, encoding="utf-8") as f:
        body = json.load(f)
    db = db_settings_from_url(os.environ.get("AUTH_DATABASE_URL") or die("AUTH_DATABASE_URL not set"))
    password = os.environ.get("GRAFANA_DB_PASSWORD") or die("GRAFANA_DB_PASSWORD not set")
    body["url"] = f"{db['host']}:{db['port']}"
    body["user"] = db["user"]
    body.setdefault("jsonData", {})["database"] = db["database"]
    body["jsonData"]["sslmode"] = db["sslmode"]
    body["secureJsonData"] = {"password": password}  # write-only in Grafana; always resend
    print(f"datasource: {db['user']}@{db['host']}:{db['port']}/{db['database']} sslmode={db['sslmode']}")

    status, existing = g.req("GET", f"/api/datasources/uid/{DATASOURCE_UID}")
    if status == 200:
        body["id"] = existing["id"]
        status, resp = g.req("PUT", f"/api/datasources/uid/{DATASOURCE_UID}", body)
        action = "updated"
    elif status == 404:
        status, resp = g.req("POST", "/api/datasources", body)
        action = "created"
    else:
        die(f"datasource lookup failed: {status} {existing}")
    if status not in (200, 201):
        die(f"datasource {action} failed: {status} {resp}")
    print(f"datasource {action}")

    status, health = g.req("GET", f"/api/datasources/uid/{DATASOURCE_UID}/health")
    if status != 200 or health.get("status") != "OK":
        die(f"datasource health check failed: {status} {health}")
    print("datasource health: OK")


# ── Dashboards ────────────────────────────────────────────────────────────────

def ensure_folder(g: Grafana, uid: str) -> None:
    status, _ = g.req("GET", f"/api/folders/{uid}")
    if status == 404:
        status, resp = g.req("POST", "/api/folders", {"uid": uid, "title": "Textara"})
        if status not in (200, 201):
            die(f"folder create failed: {status} {resp}")
        print(f"folder {uid} created")
    elif status != 200:
        die(f"folder lookup failed: {status}")


def upsert_dashboards(g: Grafana, dashboards: list[dict], folder_uid: str) -> None:
    sha = os.environ.get("GITHUB_SHA", "manual")[:12]
    for d in dashboards:
        d["id"] = None
        status, resp = g.req(
            "POST",
            "/api/dashboards/db",
            {"dashboard": d, "folderUid": folder_uid, "overwrite": True, "message": f"provision {sha}"},
        )
        if status != 200 or resp.get("status") != "success":
            die(f"dashboard {d['uid']} failed: {status} {resp}")
        print(f"dashboard {d['uid']}: v{resp.get('version')}  {g.url}{resp.get('url')}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--dashboards-only", action="store_true")
    args = ap.parse_args()

    print("validating files...")
    dashboards = validate()
    if args.validate:
        return

    g = Grafana(
        os.environ.get("GRAFANA_URL", "https://grafana.textara.app"),
        os.environ.get("GRAFANA_ADMIN_USER", "admin"),
        os.environ.get("GRAFANA_ADMIN_PASSWORD") or die("GRAFANA_ADMIN_PASSWORD not set"),
    )
    status, health = g.req("GET", "/api/health")
    if status != 200:
        die(f"Grafana unreachable: {status} {health}")
    print(f"grafana {health.get('version')} reachable")

    folder_uid = os.environ.get("GRAFANA_FOLDER_UID", "dfg912x104zcwe")
    ensure_folder(g, folder_uid)
    if not args.dashboards_only:
        upsert_datasource(g)
    upsert_dashboards(g, dashboards, folder_uid)
    print("done")


if __name__ == "__main__":
    main()
