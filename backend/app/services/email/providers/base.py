from __future__ import annotations

from abc import ABC, abstractmethod
from string import Template

from app.services.email.schemas import EmailMessage, EmailSendResult, EmailTemplatePayload


class EmailProvider(ABC):
    provider_name = "base"

    @abstractmethod
    def send_email(self, *, message: EmailMessage) -> EmailSendResult:
        raise NotImplementedError

    def send_templated_email(self, *, payload: EmailTemplatePayload) -> EmailSendResult:
        html_body = Template(payload.html_template_path.read_text(encoding="utf-8")).substitute(payload.context)
        return self.send_email(
            message=EmailMessage(
                to_email=payload.to_email,
                subject=payload.subject,
                text_body=payload.text_body,
                html_body=html_body,
                reply_to=payload.reply_to,
            )
        )


class DisabledEmailProvider(EmailProvider):
    def __init__(self, *, provider_name: str = "disabled", reason: str = "email_disabled") -> None:
        self.provider_name = provider_name
        self.reason = reason

    def send_email(self, *, message: EmailMessage) -> EmailSendResult:
        return EmailSendResult(
            success=False,
            provider=self.provider_name,
            error=self.reason,
        )
