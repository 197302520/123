#!/bin/sh
set -eu

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
target="/backups/social-network-${stamp}.dump"
pg_dump --host="${POSTGRES_HOST:-postgres}" --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --format=custom --file="$target"
find /backups -type f -name 'social-network-*.dump' -mtime "+${BACKUP_RETENTION_DAYS:-14}" -delete
echo "backup=$target retention_days=${BACKUP_RETENTION_DAYS:-14}"
