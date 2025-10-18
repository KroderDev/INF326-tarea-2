#!/bin/sh

DB_HOST="${DB_HOST:-database}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-root}"
DB_NAME="${DB_NAME:-messages_service}"

export PGPASSWORD="${PGPASSWORD:-secret}"

# Wait for Postgres to become ready (max ~60s)
i=0
while [ "$i" -lt 60 ]; do
  if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres >/dev/null 2>&1; then
    break
  fi
  i=$((i + 1))
  sleep 1
done

if ! psql -h "$DB_HOST" -U "$DB_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1; then
  psql -h "$DB_HOST" -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME;"
fi
