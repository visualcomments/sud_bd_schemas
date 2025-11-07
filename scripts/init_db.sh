#!/usr/bin/env bash
set -euo pipefail
: "${DATABASE_URL:=postgresql://postgres:postgres@localhost:5432/sudrf}"
echo "Applying extensions..."
psql "$DATABASE_URL" -f sql/ddl/01_extensions.sql
