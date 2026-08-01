FROM python:3.12-slim

RUN pip install --no-cache-dir \
    "cryptography>=43,<46" \
    "PyYAML>=6,<7"

WORKDIR /gate

COPY release-gate/release-gate.py /usr/local/bin/release-gate.py
COPY evidence/verify-evidence.py /usr/local/bin/verify-evidence.py
RUN chmod 0555 \
    /usr/local/bin/release-gate.py \
    /usr/local/bin/verify-evidence.py

ENTRYPOINT ["python", "/usr/local/bin/release-gate.py"]
