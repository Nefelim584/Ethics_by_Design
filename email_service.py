"""
email_service.py
~~~~~~~~~~~~~~~~
Thin wrapper around Flask-Mail.
Call ``init_mail(app)`` in your app factory, then use the helpers below.
"""

import logging
import os

from flask_mail import Mail, Message

logger = logging.getLogger(__name__)

mail = Mail()


def init_mail(app) -> None:
    """Configure and bind Flask-Mail to *app*."""
    app.config.update(
        MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
        MAIL_PORT=int(os.getenv("MAIL_PORT", "587")),
        MAIL_USE_TLS=os.getenv("MAIL_USE_TLS", "true").lower() == "true",
        MAIL_USE_SSL=os.getenv("MAIL_USE_SSL", "false").lower() == "true",
        MAIL_USERNAME=os.getenv("MAIL_USERNAME", ""),
        MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", "").replace(" ", ""),
        MAIL_DEFAULT_SENDER=os.getenv("MAIL_DEFAULT_SENDER", os.getenv("MAIL_USERNAME", "")),
    )
    mail.init_app(app)


# ── helpers ────────────────────────────────────────────────────────────────────

def send_email(to: str, subject: str, html_body: str, text_body: str = "") -> bool:
    """
    Send a single email.  Returns True on success, False on failure.
    Failures are logged but never raised so the caller keeps running.
    """
    try:
        msg = Message(subject=subject, recipients=[to])
        msg.html = html_body
        msg.body = text_body or _strip_html(html_body)
        mail.send(msg)
        logger.info("Email sent to %s — %s", to, subject)
        return True
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to, exc)
        return False


def send_approval_email(to: str, name: str) -> bool:
    """Notify a user that their account has been approved."""
    subject = "Your account has been approved — Ethics by Design"
    html = f"""
    <div style="font-family:Inter,system-ui,sans-serif;max-width:520px;margin:0 auto;padding:2rem 1.5rem;color:#1e293b">
      <h2 style="color:#4f46e5;margin-bottom:0.5rem">Account approved ✅</h2>
      <p style="color:#64748b;margin-bottom:1.5rem">Hi {_esc(name)},</p>
      <p>Great news — an administrator has approved your <strong>Ethics by Design</strong> account.
         You can now sign in and start using the platform.</p>
      <a href="/" style="display:inline-block;margin-top:1.5rem;padding:0.7rem 1.5rem;
         background:#4f46e5;color:#fff;border-radius:0.5rem;text-decoration:none;font-weight:600">
        Sign in now →
      </a>
      <p style="margin-top:2rem;font-size:0.8125rem;color:#94a3b8">
        If you didn't create this account, please ignore this email.
      </p>
    </div>
    """
    return send_email(to, subject, html)


def send_rejection_email(to: str, name: str) -> bool:
    """Notify a user that their account registration was declined."""
    subject = "Account registration update — Ethics by Design"
    html = f"""
    <div style="font-family:Inter,system-ui,sans-serif;max-width:520px;margin:0 auto;padding:2rem 1.5rem;color:#1e293b">
      <h2 style="color:#dc2626;margin-bottom:0.5rem">Registration declined</h2>
      <p style="color:#64748b;margin-bottom:1.5rem">Hi {_esc(name)},</p>
      <p>Unfortunately your registration request for <strong>Ethics by Design</strong>
         has been declined by an administrator.</p>
      <p style="margin-top:1rem">If you believe this is a mistake, please contact us by replying to this email.</p>
      <p style="margin-top:2rem;font-size:0.8125rem;color:#94a3b8">
        This is an automated message — please do not reply unless you have a question.
      </p>
    </div>
    """
    return send_email(to, subject, html)


def send_registration_notification_to_admin(admin_email: str, user_email: str, user_name: str) -> bool:
    """Notify the admin that a new user is awaiting approval."""
    subject = "New user pending approval — Ethics by Design"
    html = f"""
    <div style="font-family:Inter,system-ui,sans-serif;max-width:520px;margin:0 auto;padding:2rem 1.5rem;color:#1e293b">
      <h2 style="color:#4f46e5;margin-bottom:0.5rem">New registration request</h2>
      <p>A new user has registered and is awaiting your approval:</p>
      <table style="margin-top:1rem;border-collapse:collapse;width:100%">
        <tr>
          <td style="padding:0.5rem 0.75rem;font-weight:600;background:#f1f5f9;border-radius:4px 0 0 4px;white-space:nowrap">Name</td>
          <td style="padding:0.5rem 0.75rem;background:#f8fafc">{_esc(user_name)}</td>
        </tr>
        <tr>
          <td style="padding:0.5rem 0.75rem;font-weight:600;background:#f1f5f9;white-space:nowrap">Email</td>
          <td style="padding:0.5rem 0.75rem;background:#f8fafc">{_esc(user_email)}</td>
        </tr>
      </table>
      <a href="/admin" style="display:inline-block;margin-top:1.5rem;padding:0.7rem 1.5rem;
         background:#4f46e5;color:#fff;border-radius:0.5rem;text-decoration:none;font-weight:600">
        Open admin panel →
      </a>
    </div>
    """
    return send_email(admin_email, subject, html)


# ── internal utils ─────────────────────────────────────────────────────────────

def _esc(text: str) -> str:
    """Minimal HTML escaping for user-supplied strings in email bodies."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _strip_html(html: str) -> str:
    """Very basic HTML-to-plain-text fallback for the text/plain part."""
    import re
    return re.sub(r"<[^>]+>", "", html).strip()

