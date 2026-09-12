# Monitoring (Grafana as code)

The monitoring stack itself (Prometheus · Loki/Promtail · Grafana at
https://grafana.textara.app) runs in the `monitoring` namespace and is **not**
managed by this repo. What this repo owns is the product-level view on top of it:

| Path | What |
|---|---|
| `grafana/dashboards/textara-product.json` | "Textara Product" dashboard (uid `textara-product`): signups, plan mix, usage, trial funnel, OCR success/latency, Gemini tokens/cost, recent failures |
| `grafana/datasources/textara-db.json` | Read-only Postgres datasource (uid `textara-db`, user `grafana_ro`) |
| `../scripts/grafana_provision.py` | Idempotent provisioner (stdlib only): datasource upsert + dashboards into the "Textara" folder |
| `../scripts/grafana_db_role.py` | Creates/rotates the `grafana_ro` role — runs inside the auth-service pod |

## Where the numbers come from

* **Prometheus** (15-day retention) — app metrics emitted by `doc-manager`, `doc-worker`
  and `auth-service` (`textara_*`, `ocr_*`, `gemini_*`). Good for "recent" and rates.
* **Postgres** (all-time truth) — `users(id, plan, created_at, email_verified)` and
  `usage_daily`. Nothing else is readable by `grafana_ro`; emails/passwords are not
  reachable from Grafana. All transactions are forced read-only with a 15 s statement timeout.
* **Loki** — worker logs; the failure panels key on the literal `"Failed to process"` line.

Caveat: `users.created_at` was added on 2026-09-11. Accounts that existed before were
backfilled to the migration timestamp, so the "Signups / day" panel shows one artificial spike
on that day.

## How it gets applied

* Every successful deploy (`.github/workflows/deploy.yml`) runs the role script and the
  provisioner as best-effort steps (`continue-on-error`), so the dashboard survives a Grafana
  rebuild and edits made in the UI are overwritten — **edit the JSON, not the UI**.
* Manual re-run: Actions → *Grafana provision* → *Run workflow*.
* Local dry run: `python3 scripts/grafana_provision.py --validate`.
* Push dashboards only (no DB creds needed):
  `GRAFANA_ADMIN_PASSWORD=… python3 scripts/grafana_provision.py --dashboards-only`

Required GitHub secrets: `GRAFANA_ADMIN_PASSWORD`, `GRAFANA_DB_PASSWORD` (any random string —
the role script sets it on each run), `AUTH_DATABASE_URL`, `KUBECONFIG`.

## Editing the dashboard

Change it in the Grafana UI, then *Share → Export → View JSON*, paste over
`grafana/dashboards/textara-product.json`, set `"id": null`, and keep the `uid`. CI validates
the file shape. Datasource references must stay by uid (`prometheus`, `loki`, `textara-db`).
