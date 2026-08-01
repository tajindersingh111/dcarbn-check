from __future__ import annotations

import asyncio
import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TransactionalEmail:
    to_address: str
    subject: str
    text_body: str
    html_body: str | None = None


class EmailProvider(Protocol):
    async def send(self, message: TransactionalEmail) -> None:
        ...


class ConsoleEmailProvider:
    async def send(self, message: TransactionalEmail) -> None:
        logger.info(
            "transactional_email",
            extra={
                "to": message.to_address,
                "subject": message.subject,
                "text_body": message.text_body,
            },
        )


class SmtpEmailProvider:
    async def send(self, message: TransactionalEmail) -> None:
        settings = get_settings()

        def deliver() -> None:
            email = EmailMessage()
            email["From"] = settings.email_from_address
            email["To"] = message.to_address
            email["Subject"] = message.subject
            email.set_content(message.text_body)
            if message.html_body:
                email.add_alternative(message.html_body, subtype="html")

            if settings.smtp_use_tls:
                client: smtplib.SMTP = smtplib.SMTP_SSL(
                    settings.smtp_host,
                    settings.smtp_port,
                    timeout=20,
                )
            else:
                client = smtplib.SMTP(
                    settings.smtp_host,
                    settings.smtp_port,
                    timeout=20,
                )
                if settings.smtp_starttls:
                    client.starttls()

            try:
                if settings.smtp_username:
                    client.login(settings.smtp_username, settings.smtp_password)
                client.send_message(email)
            finally:
                client.quit()

        await asyncio.to_thread(deliver)


def get_email_provider() -> EmailProvider:
    settings = get_settings()
    if settings.email_provider == "smtp":
        return SmtpEmailProvider()
    return ConsoleEmailProvider()


async def send_invitation_email(
    *,
    to_address: str,
    full_name: str,
    invitation_url: str,
    tenant_name: str,
) -> None:
    await get_email_provider().send(
        TransactionalEmail(
            to_address=to_address,
            subject=f"You have been invited to {tenant_name}",
            text_body=(
                f"Hello {full_name},\n\n"
                f"Activate your D-carbN account: {invitation_url}\n\n"
                "This link is time limited."
            ),
        )
    )


async def send_password_reset_email(
    *,
    to_address: str,
    full_name: str,
    reset_url: str,
) -> None:
    await get_email_provider().send(
        TransactionalEmail(
            to_address=to_address,
            subject="Reset your D-carbN password",
            text_body=(
                f"Hello {full_name},\n\n"
                f"Reset your password: {reset_url}\n\n"
                "Ignore this message if you did not request a reset."
            ),
        )
    )
