#!/usr/bin/env bash
# Restore a backup taken by `scripts/backup.sh`.
#
# Destructive on purpose and loud about it: it drops and recreates the application
# database. A restore that merged into whatever was already there would leave a state
# that is neither the backup nor what preceded it.
#
#   ./scripts/restore.sh <backup-directory>
#
# Afterwards the learned-memory graph is empty. That is expected — it is a projection
# of rows this restore just put back — and the last step of this script rebuilds it.
set -euo pipefail
cd "$(dirname "$0")/.."

SOURCE="${1:?usage: ./scripts/restore.sh <backup-directory>}"
POSTGRES_USER="${POSTGRES_USER:-agentic}"
POSTGRES_DB="${POSTGRES_DB:-agentic_qa}"

for required in postgres.dump artifacts.tar.gz MANIFEST.txt; do
  [ -f "$SOURCE/$required" ] || { echo "missing $SOURCE/$required" >&2; exit 1; }
done

# Docker wants a host path it understands, and Git Bash rewrites anything that looks
# like one. Resolved here, once, so the rest of the script is the same on both.
host_path() {
  case "$(uname -s)" in
    MINGW* | MSYS* | CYGWIN*)
      export MSYS_NO_PATHCONV=1
      (cd "$1" && pwd -W)
      ;;
    *) (cd "$1" && pwd) ;;
  esac
}

BACKUP_HOST_PATH="$(host_path "$SOURCE")"

echo "== restoring from $SOURCE =="
cat "$SOURCE/MANIFEST.txt"
echo

# The API and worker hold connections and would write into the database mid-restore.
echo "-- stopping the writers"
docker compose stop api worker >/dev/null

echo "-- recreating $POSTGRES_DB"
docker compose exec -T postgres psql -U "$POSTGRES_USER" -d postgres \
  -c "DROP DATABASE IF EXISTS $POSTGRES_DB WITH (FORCE)" \
  -c "CREATE DATABASE $POSTGRES_DB OWNER $POSTGRES_USER" >/dev/null

echo "-- postgres"
docker compose exec -T postgres \
  pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner \
  < "$SOURCE/postgres.dump"

echo "-- artifacts"
docker run --rm \
  -v roveqa_artifact_data:/data/runs \
  -v "$BACKUP_HOST_PATH:/backup:ro" \
  alpine:3.20 sh -c 'rm -rf /data/runs/* && tar xzf /backup/artifacts.tar.gz -C /data/runs'

echo "-- starting the writers"
docker compose up -d api worker >/dev/null

echo
echo "restored. The learned-memory graph is empty until it is rebuilt from the rows"
echo "this restore put back — a projection, never the truth (ADR 0008):"
echo
echo "  curl -X POST http://localhost:8000/api/v1/projects/<project-id>/memory/rebuild"
echo
echo "Verify before trusting it:"
echo "  curl http://localhost:8000/api/v1/projects/<project-id>/memory/status"
