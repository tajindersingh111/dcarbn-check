FROM postgres:16-alpine

RUN apk add --no-cache age bash coreutils curl jq rclone tzdata

COPY backup.sh restore.sh restore-drill.sh /usr/local/bin/
RUN chmod 0555 /usr/local/bin/backup.sh \
    /usr/local/bin/restore.sh \
    /usr/local/bin/restore-drill.sh

USER postgres

ENTRYPOINT ["/usr/local/bin/backup.sh"]
