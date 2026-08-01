#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

[[ "${STANDBY_PREPARE_CONFIRMATION:-}" == "PREPARE-STANDBY-D-CARBN" ]] || {
  echo "Set STANDBY_PREPARE_CONFIRMATION=PREPARE-STANDBY-D-CARBN." >&2
  exit 1
}

export PITR_CONFIRMATION=RECOVER-D-CARBN
export PITR_TARGET_ACTION=promote
export PITR_TARGET_TIMELINE=latest
unset PITR_TARGET_TIME PITR_TARGET_LSN PITR_TARGET_XID PITR_TARGET_NAME

/usr/local/bin/restore-pitr.sh

target_dir="${PITR_TARGET_DIR:-/var/lib/postgresql/data}"
rm -f "${target_dir}/recovery.signal"
touch "${target_dir}/standby.signal"

cat >> "${target_dir}/postgresql.auto.conf" <<EOF
hot_standby = on
primary_conninfo = ''
EOF

echo "Archive-fed standby data directory prepared."
