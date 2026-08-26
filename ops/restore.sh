#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "usage: restore.sh /backups/social-network-TIMESTAMP.dump" >&2
  exit 2
fi

BACKUP_ROOT="${BACKUP_ROOT:-/backups}"
backup_root="$(readlink -f -- "$BACKUP_ROOT")" || exit 2
source="$(readlink -f -- "$1")" || exit 2

case "$source" in
  "$backup_root"/social-network-*.dump) ;;
  *) echo "restore source must resolve to a named dump under $backup_root" >&2; exit 2 ;;
esac

[ -f "$source" ] || { echo "restore source must be a regular file" >&2; exit 2; }
pg_restore --host="${POSTGRES_HOST:-postgres}" --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" \
  --clean --if-exists --no-owner --single-transaction "$source"
