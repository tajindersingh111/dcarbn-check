FROM postgres:16-alpine

RUN apk add --no-cache age bash coreutils jq rclone util-linux && \
    mkdir -p /base-backups /status /pitr-status /recovery-data && \
    chown -R postgres:postgres \
      /base-backups /status /pitr-status /recovery-data

COPY create-base-backup.sh restore-pitr.sh validate-recovery.sh prepare-standby.sh /usr/local/bin/
RUN chmod 0555 \
    /usr/local/bin/create-base-backup.sh \
    /usr/local/bin/restore-pitr.sh \
    /usr/local/bin/validate-recovery.sh \
    /usr/local/bin/prepare-standby.sh

USER postgres
