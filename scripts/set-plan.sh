#!/usr/bin/env bash
# Grant or revoke Pro for a single account, by email.
#
#   ./scripts/set-plan.sh someone@example.com pro
#   ./scripts/set-plan.sh someone@example.com free
#   ./scripts/set-plan.sh someone@example.com          # just look them up
#
# Needs ADMIN_API_KEY. It is stored as a GitHub Actions secret (write-only), so
# read it from the cluster:
#   export ADMIN_API_KEY=$(ssh -i ~/.ssh/oracle-ssh.key ubuntu@40.233.116.127 \
#     "sudo kubectl get secret auth-service-secret -n textara \
#      -o jsonpath='{.data.ADMIN_API_KEY}'" | base64 -d)
#
# NOTE: this sets the plan directly and does NOT create a Stripe subscription.
# The account gets Pro with nothing to bill and nothing to cancel — which is what
# you want for a comped or beta account. Two consequences worth knowing:
#   * It never expires. Set it back to "free" by hand when you mean to end it.
#   * It is indistinguishable from a paying customer in the database, so a comped
#     account will look like a conversion in any revenue stat you compute.
set -euo pipefail

BASE="${TEXTARA_API:-https://textara.app/api/auth/v1}"
EMAIL="${1:-}"
PLAN="${2:-}"

if [ -z "$EMAIL" ]; then
  echo "usage: $0 <email> [pro|free]" >&2
  exit 1
fi
if [ -z "${ADMIN_API_KEY:-}" ]; then
  echo "ADMIN_API_KEY is not set — see the comment at the top of this script." >&2
  exit 1
fi
if [ -n "$PLAN" ] && [ "$PLAN" != "pro" ] && [ "$PLAN" != "free" ]; then
  echo "plan must be 'pro' or 'free' (got '$PLAN')" >&2
  exit 1
fi

user=$(curl -fsS -H "X-Admin-Key: $ADMIN_API_KEY" \
  --get --data-urlencode "email=$EMAIL" "$BASE/admin/users") || {
    echo "No account found for $EMAIL" >&2; exit 1; }

id=$(printf '%s' "$user" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
current=$(printf '%s' "$user" | python3 -c 'import json,sys; print(json.load(sys.stdin)["plan"])')

if [ -z "$PLAN" ]; then
  printf '%s\n' "$user" | python3 -m json.tool
  exit 0
fi

if [ "$current" = "$PLAN" ]; then
  echo "$EMAIL (id=$id) is already on '$PLAN' — nothing to do."
  exit 0
fi

curl -fsS -X PUT -H "X-Admin-Key: $ADMIN_API_KEY" -H "Content-Type: application/json" \
  -d "{\"plan\":\"$PLAN\"}" "$BASE/admin/users/$id/plan" >/dev/null

echo "$EMAIL (id=$id): $current -> $PLAN"
