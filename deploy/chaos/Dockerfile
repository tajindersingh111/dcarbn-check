FROM alpine:3.20

RUN apk add --no-cache bash curl docker-cli iproute2 jq netcat-openbsd postgresql16-client

COPY chaos.sh /usr/local/bin/chaos.sh
RUN chmod 0555 /usr/local/bin/chaos.sh

ENTRYPOINT ["/usr/local/bin/chaos.sh"]
