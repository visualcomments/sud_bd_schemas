#!/usr/bin/env bash
set -euo pipefail
: "${DATABASE_URL:=postgresql://postgres:postgres@localhost:5432/sudrf}"
for f in sql/migrations/*.sql; do
  echo "Applying $f"
  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$f"
done
