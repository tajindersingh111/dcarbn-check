#!/usr/bin/env bash
set -Eeuo pipefail

mkdir -p \
  "${WAL_ARCHIVE_LOCAL_DIR:-/wal-archive}" \
  "${WAL_ARCHIVE_STATUS_DIR:-/wal-status}"

if [[ "$(id -u)" == "0" ]]; then
  chown -R postgres:postgres \
    "${WAL_ARCHIVE_LOCAL_DIR:-/wal-archive}" \
    "${WAL_ARCHIVE_STATUS_DIR:-/wal-status}"
fi

exec /usr/local/bin/docker-entrypoint.sh "$@"
