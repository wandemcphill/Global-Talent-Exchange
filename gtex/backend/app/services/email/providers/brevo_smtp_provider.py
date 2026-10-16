from __future__ import annotations

from email.message import EmailMessage as MimeEmailMessage
from email.utils import formataddr, make_msgid
import logging
import smtplib

from app.services.email.providers.base import EmailProvider
from app.services.email.schemas import EmailMessage, EmailSendResult

logger = logging.getLogger(__name__)


class BrevoSmtpProvider(EmailProvider):
    provider_name = "brevo_smtp"

    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        from_address: str,
        from_name: str,
        reply_to: str | None,
        timeout_seconds: int,
        use_tls: bool,
        use_ssl: bool,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.from_address = from_address
        self.from_name = from_name
        self.reply_to = reply_to
        self.timeout_seconds = timeout_seconds
        self.use_tls = use_tls
        self.use_ssl = use_ssl

    def send_email(self, *, message: EmailMessage) -> EmailSendResult:
        if not self.password:
            return EmailSendResult(success=False, provider=self.provider_name, error="smtp_password_missing")

        smtp_client_class = smtplib.SMTP_SSL if self.use_ssl else smtplib.SMTP
        mime_message = self._build_message(message)

        try:
            with smtp_client_class(self.host, self.port, timeout=self.timeout_seconds) as client:
                client.ehlo()
                if self.use_tls and not self.use_ssl:
                    client.starttls()
                    client.ehlo()
                client.login(self.username, self.password)
                client.send_message(mime_message)
        except Exception as exc:
            sanitized_error = self._sanitize_error_message(str(exc))
            logger.warning(
                "email.send.failed provider=%s host=%s port=%s recipient=%s error_type=%s error=%s",
                self.provider_name,
                self.host,
                self.port,
                message.to_email,
                exc.__class__.__name__,
                sanitized_error,
            )
            return EmailSendResult(
                success=False,
                provider=self.provider_name,
                message_id=mime_message["Message-ID"],
                error=sanitized_error or exc.__class__.__name__,
            )

        return EmailSendResult(
            success=True,
            provider=self.provider_name,
            message_id=mime_message["Message-ID"],
        )

    def _build_message(self, message: EmailMessage) -> MimeEmailMessage:
        mime_message = MimeEmailMessage()
        mime_message["Subject"] = message.subject
        mime_message["From"] = formataddr((self.from_name, self.from_address))
        mime_message["To"] = message.to_email
        mime_message["Message-ID"] = make_msgid(domain=self.from_address.split("@", maxsplit=1)[-1])

        reply_to = message.reply_to or self.reply_to
        if reply_to:
            mime_message["Reply-To"] = reply_to

        mime_message.set_content(message.text_body)
        if message.html_body:
            mime_message.add_alternative(message.html_body, subtype="html")
        return mime_message

    def _sanitize_error_message(self, value: str) -> str:
        sanitized = value
        if self.password:
            sanitized = sanitized.replace(self.password, "[redacted]")
        return sanitized
