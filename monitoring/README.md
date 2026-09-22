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

## Alerting

Rules live in `monitoring/grafana/alerting/textara-alerts.json` and are provisioned
by `scripts/grafana_provision.py` alongside the dashboards. They are **Grafana-managed**
rules, not Alertmanager — one fewer component to run on a single free-tier node, and
Grafana's contact points cover Telegram, ntfy and webhooks out of the box.

### Delivery

Set the `ALERT_WEBHOOK_URL` GitHub secret to a Telegram bot or [ntfy.sh](https://ntfy.sh)
topic URL, then run the **Grafana provision** workflow. Without it the rules are still
created, but nothing routes and they fire into the void.

**Do not route these to email.** The first rule fires when email is broken, and an
email alert about broken email cannot arrive. That recursion is exactly why the
September 2026 SendGrid outage ran for weeks undetected.

### Still manual

Two pieces of monitoring config are not in this repo — they exist only as live
ConfigMaps (`prometheus-config`, `loki-config`) and predate this directory:

- **`loki-config` sets `retention_period: 720h` but the compactor has
  `retention_enabled: false`**, so nothing is ever deleted. Every log line since day
  one is still on disk, on a node that is ~72% full. Fix: add a `compactor` block with
  `retention_enabled: true` and `delete_request_store: filesystem`.
- **`prometheus-config` still scrapes `ocr-worker-desktop`**, a static target pointing
  at a developer desktop that no longer exists. `up` for it is permanently 0, so any
  bare `up == 0` alert fires forever. The rules here scope to
  `job="kubernetes-pods"` to work around it, but the job should be deleted.

Both need a deliberate `kubectl edit` plus a pod restart, so they are called out here
rather than applied automatically.

### External heartbeat

Nothing inside the cluster can tell you the cluster is gone. Add a free
[healthchecks.io](https://healthchecks.io) check pinged from a Grafana webhook contact
point, or an UptimeRobot check against `https://textara.app`, so a dead node still
reaches you.
