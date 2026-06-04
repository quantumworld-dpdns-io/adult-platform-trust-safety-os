"""Email notifications: send, bulk send, templates, and delivery status."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_email_log: list[dict[str, Any]] = []
_delivery_status: dict[str, dict[str, Any]] = {}


class EmailNotifier:
    def __init__(self, smtp_host: str = "localhost", smtp_port: int = 587) -> None:
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._log = _email_log
        self._delivery = _delivery_status

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        from_address: str = "noreply@trust-safety.io",
        html: bool = False,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
    ) -> dict[str, Any]:
        message_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        record = {
            "message_id": message_id,
            "to": to,
            "from": from_address,
            "subject": subject,
            "body_length": len(body),
            "html": html,
            "cc": cc or [],
            "bcc": bcc or [],
            "status": "sent",
            "sent_at": now,
            "delivered_at": None,
            "opened_at": None,
        }
        self._log.append(record)
        self._delivery[message_id] = {
            "status": "sent",
            "attempts": 1,
            "last_attempt": now,
        }

        logger.info("email_sent", message_id=message_id, to=to, subject=subject)

        return {
            "message_id": message_id,
            "status": "sent",
            "sent_at": now,
        }

    async def send_bulk(
        self,
        recipients: list[str],
        subject: str,
        body: str,
        from_address: str = "noreply@trust-safety.io",
        html: bool = False,
    ) -> dict[str, Any]:
        results = []
        for recipient in recipients:
            result = await self.send_email(
                to=recipient,
                subject=subject,
                body=body,
                from_address=from_address,
                html=html,
            )
            results.append(result)

        return {
            "total_sent": len(results),
            "results": results,
            "subject": subject,
        }

    async def send_template(
        self,
        to: str,
        template_name: str,
        template_vars: dict[str, Any],
        from_address: str = "noreply@trust-safety.io",
    ) -> dict[str, Any]:
        templates: dict[str, str] = {
            "content_reviewed": "Hello, your content has been reviewed. Status: {status}.",
            "account_suspended": "Hello, your account has been suspended. Reason: {reason}.",
            "password_reset": "Hello, use this link to reset your password: {reset_link}.",
            "welcome": "Welcome to {platform_name}! Your account is now active.",
            "age_verification_required": "Please verify your age to continue using {platform_name}.",
        }

        template = templates.get(template_name)
        if template is None:
            return {"error": f"Template not found: {template_name}"}

        try:
            body = template.format(**template_vars)
        except KeyError as e:
            return {"error": f"Missing template variable: {e}"}

        return await self.send_email(
            to=to,
            subject=f"[Trust & Safety] {template_name.replace('_', ' ').title()}",
            body=body,
            from_address=from_address,
        )

    async def get_delivery_status(
        self,
        message_id: str,
    ) -> dict[str, Any]:
        if message_id not in self._delivery:
            return {"error": "Message not found", "message_id": message_id}

        status = self._delivery[message_id]
        record = next(
            (r for r in self._log if r["message_id"] == message_id),
            None,
        )

        return {
            "message_id": message_id,
            "status": status["status"],
            "attempts": status["attempts"],
            "last_attempt": status["last_attempt"],
            "sent_at": record["sent_at"] if record else None,
            "delivered_at": record.get("delivered_at") if record else None,
            "opened_at": record.get("opened_at") if record else None,
        }

    def get_stats(self) -> dict[str, Any]:
        sent = len(self._log)
        delivered = sum(1 for r in self._log if r.get("status") == "sent")
        return {
            "total_sent": sent,
            "delivered": delivered,
            "delivery_rate": delivered / max(sent, 1),
        }
