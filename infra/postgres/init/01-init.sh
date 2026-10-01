#!/usr/bin/env bash
set -euo pipefail

# The PostgreSQL official image runs this script only when the data directory is
# initialized for the first time. Separate users/databases keep TrueForge and
# KiN from sharing application-level privileges.

psql_base=(psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres)

"${psql_base[@]}" \
  -v kin_user="$KiN_DB_USER" \
  -v kin_pass="$KiN_DB_PASSWORD" \
  -v kin_db="$KiN_DB_NAME" \
  -v forge_user="$TRUEFORGE_DB_USER" \
  -v forge_pass="$TRUEFORGE_DB_PASSWORD" \
  -v forge_db="$TRUEFORGE_DB_NAME" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'kin_user', :'kin_pass')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'kin_user')\gexec

SELECT format('CREATE DATABASE %I OWNER %I', :'kin_db', :'kin_user')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'kin_db')\gexec

SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'forge_user', :'forge_pass')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'forge_user')\gexec

SELECT format('CREATE DATABASE %I OWNER %I', :'forge_db', :'forge_user')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'forge_db')\gexec
SQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$KiN_DB_NAME" <<'SQL'
CREATE EXTENSION IF NOT EXISTS vector;
GRANT USAGE ON SCHEMA public TO PUBLIC;
SQL
