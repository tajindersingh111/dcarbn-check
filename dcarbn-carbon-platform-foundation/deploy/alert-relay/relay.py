from __future__ import annotations

import json
import os
import smtplib
import urllib.request
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


def read_secret(name: str) -> str:
    file_path = os.getenv(f"{name}_FILE")
    if file_path and Path(file_path).is_file():
        return Path(file_path).read_text(encoding="utf-8").strip()
    return os.getenv(name, "")


def format_alerts(payload: dict[str, Any]) -> tuple[str, str]:
    alerts = payload.get("alerts", [])
    status = str(payload.get("status", "unknown")).upper()
    lines = [f"D-carbN alerts: {status}", ""]
    for alert in alerts:
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        lines.extend(
            [
                f"Alert: {labels.get('alertname', 'unknown')}",
                f"Severity: {labels.get('severity', 'unknown')}",
                f"Service: {labels.get('service', 'unknown')}",
                f"Summary: {annotations.get('summary', '')}",
                f"Runbook: {annotations.get('runbook_url', '')}",
                f"Starts: {alert.get('startsAt', '')}",
                "",
            ]
        )
    subject = f"[{status}] D-carbN operational alert"
    return subject, "\n".join(lines)


def deliver_email(subject: str, body: str) -> None:
    recipient = os.getenv("ALERT_EMAIL_TO", "")
    if not recipient:
        return

    message = EmailMessage()
    message["From"] = os.getenv("ALERT_EMAIL_FROM", "alerts@example.com")
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    host = os.getenv("SMTP_HOST", "")
    port = int(os.getenv("SMTP_PORT", "465"))
    username = os.getenv("SMTP_USERNAME", "")
    password = read_secret("SMTP_PASSWORD")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    if use_tls:
        client: smtplib.SMTP = smtplib.SMTP_SSL(host, port, timeout=20)
    else:
        client = smtplib.SMTP(host, port, timeout=20)

    try:
        if username:
            client.login(username, password)
        client.send_message(message)
    finally:
        client.quit()


def deliver_webhook(payload: dict[str, Any]) -> None:
    url = os.getenv("ALERT_FORWARD_WEBHOOK_URL", "")
    if not url:
        return
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20):
        pass


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path not in {"/alerts", "/critical"}:
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            subject, body = format_alerts(payload)
            deliver_email(subject, body)
            deliver_webhook(payload)
        except Exception as exc:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(type(exc).__name__).encode("utf-8"))
            return

        self.send_response(204)
        self.end_headers()

    def log_message(self, message: str, *args: object) -> None:
        print(json.dumps({"message": message % args}))


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
