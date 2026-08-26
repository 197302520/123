#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "usage: restore.sh /backups/social-network-TIMESTAMP.dump" >&2
  exit 2
fi

case "$1" in
  /backups/social-network-*.dump) ;;
  *) echo "restore source must be a named dump under /backups" >&2; exit 2 ;;
esac

test -f "$1"
pg_restore --host="${POSTGRES_HOST:-postgres}" --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --clean --if-exists --no-owner "$1"
