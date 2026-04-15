from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Optional


class Mailer:
    def __init__(self, runtime_dir: Path) -> None:
        self.runtime_dir = runtime_dir
        self.outbox_dir = runtime_dir / "outbox"
        self.outbox_dir.mkdir(parents=True, exist_ok=True)

    def send_mail(self, recipient: str, subject: str, body: str) -> dict:
        smtp_host = os.getenv("WORKBENCH_SMTP_HOST")
        smtp_port = int(os.getenv("WORKBENCH_SMTP_PORT", "587"))
        smtp_username = os.getenv("WORKBENCH_SMTP_USERNAME")
        smtp_password = os.getenv("WORKBENCH_SMTP_PASSWORD")
        smtp_sender = os.getenv("WORKBENCH_SMTP_SENDER", smtp_username or "no-reply@workbench.local")
        use_tls = os.getenv("WORKBENCH_SMTP_TLS", "1") != "0"

        if smtp_host and smtp_username and smtp_password:
            message = EmailMessage()
            message["From"] = smtp_sender
            message["To"] = recipient
            message["Subject"] = subject
            message.set_content(body)
            with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
                if use_tls:
                    server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(message)
            return {"status": "sent", "transport": "smtp"}

        safe_name = recipient.replace("@", "_at_").replace(".", "_")
        file_path = self.outbox_dir / f"{safe_name}.txt"
        file_path.write_text(f"To: {recipient}\nSubject: {subject}\n\n{body}\n", encoding="utf-8")
        return {"status": "captured", "transport": "file", "path": str(file_path.resolve())}

    def send_login_code(self, recipient: str, code: str, display_name: Optional[str] = None) -> dict:
        name = display_name or "there"
        subject = "Your Anomaly Detection Workbench verification code"
        body = (
            f"Hi {name},\n\n"
            f"Your verification code is: {code}\n\n"
            "It expires in 5 minutes. If you did not try to sign in, you can ignore this email.\n"
        )
        return self.send_mail(recipient, subject, body)

    def send_reset_link(self, recipient: str, reset_link: str, display_name: Optional[str] = None) -> dict:
        name = display_name or "there"
        subject = "Reset your Anomaly Detection Workbench password"
        body = (
            f"Hi {name},\n\n"
            "We received a request to reset your password.\n"
            f"Use this link to continue:\n{reset_link}\n\n"
            "This link expires in 30 minutes. If you did not request a reset, you can ignore this email.\n"
        )
        return self.send_mail(recipient, subject, body)
