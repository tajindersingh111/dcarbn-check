FROM postgres:16-alpine

RUN apk add --no-cache age bash coreutils curl jq rclone util-linux

COPY archive-wal.sh restore-wal.sh primary-entrypoint.sh /usr/local/bin/
RUN chmod 0555 \
    /usr/local/bin/archive-wal.sh \
    /usr/local/bin/restore-wal.sh \
    /usr/local/bin/primary-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/primary-entrypoint.sh"]
CMD ["postgres"]
