FROM alpine:3.20

ARG SYFT_VERSION=1.18.1
ARG GRYPE_VERSION=0.85.0
ARG TRIVY_VERSION=0.58.1
ARG COSIGN_VERSION=2.4.1
ARG YQ_VERSION=4.44.6

RUN apk add --no-cache bash curl docker-cli jq python3 py3-yaml && \
    curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh \
      | sh -s -- -b /usr/local/bin "v${SYFT_VERSION}" && \
    curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh \
      | sh -s -- -b /usr/local/bin "v${GRYPE_VERSION}" && \
    curl -sSfL \
      "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz" \
      | tar -xz -C /usr/local/bin trivy && \
    curl -sSfL \
      "https://github.com/sigstore/cosign/releases/download/v${COSIGN_VERSION}/cosign-linux-amd64" \
      -o /usr/local/bin/cosign && \
    curl -sSfL \
      "https://github.com/mikefarah/yq/releases/download/v${YQ_VERSION}/yq_linux_amd64" \
      -o /usr/local/bin/yq && \
    chmod 0555 /usr/local/bin/cosign /usr/local/bin/yq

COPY . /scripts
RUN chmod 0555 /scripts/*.sh

ENTRYPOINT ["/bin/bash"]
