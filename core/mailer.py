"""Envío de correo por SMTP (opcional)."""
import smtplib
from email.message import EmailMessage

from core.config import get_section

_KEYS = ["host", "port", "user", "password", "sender"]


def is_configured() -> bool:
    cfg = get_section("smtp", _KEYS)
    return all(k in cfg for k in ("host", "user", "password"))


def send_email(to: str, subject: str, body: str) -> None:
    cfg = get_section("smtp", _KEYS)
    if not is_configured():
        raise RuntimeError("SMTP no configurado.")
    port = int(cfg.get("port", 587))
    msg = EmailMessage()
    msg["From"] = cfg.get("sender", cfg["user"])
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    if port == 465:
        with smtplib.SMTP_SSL(cfg["host"], port, timeout=20) as server:
            server.login(cfg["user"], str(cfg["password"]))
            server.send_message(msg)
    else:
        with smtplib.SMTP(cfg["host"], port, timeout=20) as server:
            server.starttls()
            server.login(cfg["user"], str(cfg["password"]))
            server.send_message(msg)
