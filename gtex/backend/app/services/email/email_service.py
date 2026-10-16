from __future__ import annotations

from html import escape
from pathlib import Path
from urllib.parse import urlencode

from app.core.config import BrevoSmtpConfig, EmailConfig, Settings
from app.services.email.providers.base import DisabledEmailProvider, EmailProvider
from app.services.email.providers.brevo_smtp_provider import BrevoSmtpProvider
from app.services.email.schemas import EmailSendResult, EmailTemplatePayload


def _default_email_config() -> EmailConfig:
    return EmailConfig(
        enabled=False,
        provider="disabled",
        from_address="vidzimedialtd@gmail.com",
        from_name="GTEX",
        reply_to="vidzimedialtd@gmail.com",
        send_timeout_seconds=15,
        signup_confirmation_ttl_minutes=1440,
        account_recovery_ttl_minutes=30,
        signup_confirmation_url_base=None,
        account_recovery_url_base=None,
        brevo_smtp=BrevoSmtpConfig(
            host="smtp-relay.brevo.com",
            port=587,
            username="a21b41001@smtp-brevo.com",
            password="",
            use_tls=True,
            use_ssl=False,
        ),
    )


class EmailService:
    def __init__(
        self,
        *,
        provider: EmailProvider | None = None,
        config: EmailConfig | None = None,
        templates_root: Path | None = None,
    ) -> None:
        self.config = config or _default_email_config()
        self.provider = provider or _build_provider(self.config)
        self.templates_root = templates_root or Path(__file__).resolve().parent / "templates"
        self.signup_confirmation_ttl_minutes = self.config.signup_confirmation_ttl_minutes
        self.account_recovery_ttl_minutes = self.config.account_recovery_ttl_minutes

    @classmethod
    def build(cls, settings: Settings) -> "EmailService":
        return cls(config=settings.email)

    @classmethod
    def disabled(cls) -> "EmailService":
        return cls(config=_default_email_config())

    def build_signup_confirmation_link(self, confirmation_code: str) -> str | None:
        return self._build_link(self.config.signup_confirmation_url_base, code=confirmation_code)

    def build_account_recovery_link(self, recovery_code: str) -> str | None:
        return self._build_link(self.config.account_recovery_url_base, code=recovery_code)

    def send_signup_confirmation_email(
        self,
        to_email: str,
        confirmation_code_or_link: str,
        *,
        recipient_name: str | None = None,
        confirmation_link: str | None = None,
    ) -> EmailSendResult:
        subject = "Confirm your GTEX account"
        recipient_label = recipient_name or "there"
        action_label = "Confirm your account"
        text_body = self._build_signup_text_body(
            recipient_name=recipient_label,
            confirmation_code=confirmation_code_or_link,
            confirmation_link=confirmation_link,
        )
        return self.provider.send_templated_email(
            payload=EmailTemplatePayload(
                to_email=to_email,
                subject=subject,
                text_body=text_body,
                html_template_path=self.templates_root / "signup_confirmation.html",
                reply_to=self.config.reply_to,
                context=self._build_html_context(
                    recipient_name=recipient_label,
                    headline="Confirm your GTEX account",
                    intro="Use the confirmation code below to finish verifying your new GTEX account.",
                    code_label="Confirmation code",
                    code_value=confirmation_code_or_link,
                    action_label=action_label,
                    action_url=confirmation_link,
                    fallback_text="If the button does not work, copy the confirmation code into the confirmation screen.",
                    security_note="If you did not create this account, you can ignore this email.",
                ),
            )
        )

    def send_account_recovery_email(
        self,
        to_email: str,
        recovery_code_or_link: str,
        *,
        recipient_name: str | None = None,
        recovery_link: str | None = None,
    ) -> EmailSendResult:
        subject = "Recover your GTEX account"
        recipient_label = recipient_name or "there"
        action_label = "Recover your account"
        text_body = self._build_account_recovery_text_body(
            recipient_name=recipient_label,
            recovery_code=recovery_code_or_link,
            recovery_link=recovery_link,
        )
        return self.provider.send_templated_email(
            payload=EmailTemplatePayload(
                to_email=to_email,
                subject=subject,
                text_body=text_body,
                html_template_path=self.templates_root / "account_recovery.html",
                reply_to=self.config.reply_to,
                context=self._build_html_context(
                    recipient_name=recipient_label,
                    headline="Recover your GTEX account",
                    intro="Use the recovery code below to reset your password and regain access to your account.",
                    code_label="Recovery code",
                    code_value=recovery_code_or_link,
                    action_label=action_label,
                    action_url=recovery_link,
                    fallback_text="If the button does not work, copy the recovery code into the password reset screen.",
                    security_note="If you did not request account recovery, ignore this email and your password will stay unchanged.",
                ),
            )
        )

    def _build_signup_text_body(
        self,
        *,
        recipient_name: str,
        confirmation_code: str,
        confirmation_link: str | None,
    ) -> str:
        lines = [
            f"Hi {recipient_name},",
            "",
            "Confirm your GTEX account with the code below:",
            confirmation_code,
        ]
        if confirmation_link:
            lines.extend(["", f"Confirmation link: {confirmation_link}"])
        lines.extend(
            [
                "",
                "If the link fails, enter the confirmation code manually.",
                "If you did not create this account, you can ignore this email.",
            ]
        )
        return "\n".join(lines)

    def _build_account_recovery_text_body(
        self,
        *,
        recipient_name: str,
        recovery_code: str,
        recovery_link: str | None,
    ) -> str:
        lines = [
            f"Hi {recipient_name},",
            "",
            "Use the recovery code below to reset your GTEX password:",
            recovery_code,
        ]
        if recovery_link:
            lines.extend(["", f"Recovery link: {recovery_link}"])
        lines.extend(
            [
                "",
                "If the link fails, enter the recovery code manually.",
                "If you did not request account recovery, ignore this email and your password will remain unchanged.",
            ]
        )
        return "\n".join(lines)

    def _build_html_context(
        self,
        *,
        recipient_name: str,
        headline: str,
        intro: str,
        code_label: str,
        code_value: str,
        action_label: str,
        action_url: str | None,
        fallback_text: str,
        security_note: str,
    ) -> dict[str, str]:
        return {
            "brand_name": escape(self.config.from_name),
            "recipient_name": escape(recipient_name),
            "headline": escape(headline),
            "intro": escape(intro),
            "code_label": escape(code_label),
            "code_value": escape(code_value),
            "action_block": self._build_action_block(action_label=action_label, action_url=action_url),
            "fallback_text": escape(fallback_text),
            "security_note": escape(security_note),
        }

    def _build_action_block(self, *, action_label: str, action_url: str | None) -> str:
        if not action_url:
            return ""
        return (
            '<p style="margin: 24px 0;">'
            f'<a href="{escape(action_url, quote=True)}" '
            'style="display: inline-block; background: #111827; color: #ffffff; text-decoration: none; '
            'padding: 12px 18px; border-radius: 8px; font-weight: 600;">'
            f"{escape(action_label)}"
            "</a></p>"
        )

    @staticmethod
    def _build_link(base_url: str | None, *, code: str) -> str | None:
        if not base_url:
            return None
        separator = "&" if "?" in base_url else "?"
        return f"{base_url}{separator}{urlencode({'code': code})}"


def _build_provider(config: EmailConfig) -> EmailProvider:
    if not config.enabled:
        return DisabledEmailProvider(reason="email_disabled")
    if config.provider == "brevo_smtp":
        return BrevoSmtpProvider(
            host=config.brevo_smtp.host,
            port=config.brevo_smtp.port,
            username=config.brevo_smtp.username,
            password=config.brevo_smtp.password,
            from_address=config.from_address,
            from_name=config.from_name,
            reply_to=config.reply_to,
            timeout_seconds=config.send_timeout_seconds,
            use_tls=config.brevo_smtp.use_tls,
            use_ssl=config.brevo_smtp.use_ssl,
        )
    return DisabledEmailProvider(provider_name=config.provider, reason="unsupported_email_provider")
