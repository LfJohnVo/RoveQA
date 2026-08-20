#!/usr/bin/env bash
# Back up the two things that cannot be rebuilt: PostgreSQL and the evidence bytes.
#
# What is deliberately *not* here is as important as what is. FalkorDB holds a
# projection of knowledge that PostgreSQL already owns (ADR 0008), so backing it up
# would create a second copy free to disagree with the first; after a restore it is
# rebuilt, and `scripts/restore.sh` says so. Temporal keeps its own state in its own
# store and its own backup story. Redis is ephemeral by design.
#
#   ./scripts/backup.sh [destination-directory]
#
# Requires the stack to be up (`make up`): the dump is taken through the running
# postgres container, so it uses the same version that wrote the data.
set -euo pipefail
cd "$(dirname "$0")/.."

DESTINATION="${1:-backups/$(date -u +%Y%m%dT%H%M%SZ)}"
POSTGRES_USER="${POSTGRES_USER:-agentic}"
POSTGRES_DB="${POSTGRES_DB:-agentic_qa}"

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

mkdir -p "$DESTINATION"
BACKUP_HOST_PATH="$(host_path "$DESTINATION")"
echo "== backing up into $DESTINATION =="

# Custom format: restorable selectively, and compressed without a second tool.
echo "-- postgres ($POSTGRES_DB)"
docker compose exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom \
  > "$DESTINATION/postgres.dump"

# The bytes referenced by the `artifacts` table. A backup of one without the other
# restores a database full of pointers to nothing.
echo "-- artifacts"
docker run --rm \
  -v roveqa_artifact_data:/data/runs:ro \
  -v "$BACKUP_HOST_PATH:/backup" \
  alpine:3.20 sh -c 'tar czf /backup/artifacts.tar.gz -C /data/runs .'

# The schema version this dump belongs to. Restoring into a different one is the
# failure that turns a backup into a puzzle, so it is recorded rather than remembered.
echo "-- schema version"
docker compose --profile gates run --rm -T backend-tests \
  alembic current 2>/dev/null | tail -1 > "$DESTINATION/alembic-revision.txt"

cat > "$DESTINATION/MANIFEST.txt" <<MANIFEST
taken_at   $(date -u +%Y-%m-%dT%H:%M:%SZ)
database   $POSTGRES_DB
revision   $(cat "$DESTINATION/alembic-revision.txt")
contents   postgres.dump, artifacts.tar.gz
excluded   falkordb (rebuildable from postgres), temporal (own store), redis (ephemeral)
MANIFEST

echo
cat "$DESTINATION/MANIFEST.txt"
echo
echo "backup complete: $DESTINATION"
