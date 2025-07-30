#!/bin/bash

set -e

MSG="$1"
DATE=$(date +%Y%m%d)
OUT_FILE="supabase/migrations/${DATE}_${MSG// /_}.sql"

if [ -z "$MSG" ]; then
  echo "Usage: ./migrate.sh 'migration message'"
  exit 1
fi

echo "Generating Alembic migration..."
alembic revision --autogenerate -m "$MSG"

echo "Applying migration to local DB..."
alembic upgrade head

echo "Exporting SQL for Supabase..."
mkdir -p supabase/migrations
alembic upgrade head --sql > "$OUT_FILE"

echo "Done. Migration exported to:"
echo "$OUT_FILE"
