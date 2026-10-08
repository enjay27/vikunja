#!/usr/bin/env bash
# Writes a Vikunja dump (settings, database and files) into ./backups and deletes dumps older
# than 14 days. Run it from the project folder on the NAS by a Task Scheduler job, and copy
# ./backups somewhere that is not this NAS (README, "Backups").
set -euo pipefail
cd "$(dirname "$0")/.."
# DSM's Container Manager may only have the hyphenated docker-compose.
if docker compose version >/dev/null 2>&1; then compose="docker compose"; else compose="docker-compose"; fi
$compose exec -T vikunja /app/vikunja/vikunja dump -p /backups
find backups -name '*.zip' -mtime +14 -delete
ls -l backups
