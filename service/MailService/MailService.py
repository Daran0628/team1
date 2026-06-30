import email
import imaplib
import os
import smtplib
import ssl
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

MAILCOW_API_URL = os.getenv("MAILCOW_API_URL", "https://192.168.56.102:8443/api/v1")
MAILCOW_API_KEY = os.getenv("MAILCOW_API_KEY", "")
MAIL_DOMAIN     = os.getenv("MAIL_DOMAIN", "1mail.local")
IMAP_HOST       = os.getenv("IMAP_HOST", "192.168.56.102")
IMAP_PORT       = int(os.getenv("IMAP_PORT", "993"))
SMTP_HOST       = os.getenv("SMTP_HOST", "192.168.56.102")
SMTP_PORT       = int(os.getenv("SMTP_PORT", "587"))


def _mail_password(account_id: str) -> str:
    return f"Mail_{account_id}_2024!"


def _decode_str(value: str) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    result = []
    for part, charset in parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return "".join(result)


def _imap_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


class MailService:

    def create_mailbox(self, account_id: str, name_ko: str) -> bool:
        resp = requests.post(
            f"{MAILCOW_API_URL}/add/mailbox",
            headers={"X-API-Key": MAILCOW_API_KEY, "Content-Type": "application/json"},
            json={
                "local_part": account_id,
                "domain":     MAIL_DOMAIN,
                "name":       name_ko,
                "password":   _mail_password(account_id),
                "password2":  _mail_password(account_id),
                "quota":      "1024",
                "active":     "1",
            },
            verify=False,
            timeout=10,
        )
        if resp.status_code != 200:
            return False
        result = resp.json()
        if isinstance(result, list) and result:
            return result[0].get("type") == "success"
        return False

    def get_inbox(self, account_id: str) -> list:
        with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, ssl_context=_imap_context()) as imap:
            imap.login(f"{account_id}@{MAIL_DOMAIN}", _mail_password(account_id))
            imap.select("INBOX")

            _, data = imap.search(None, "ALL")
            uids = data[0].split()
            uids = uids[-30:] if len(uids) > 30 else uids

            messages = []
            for uid in reversed(uids):
                _, msg_data = imap.fetch(uid, "(RFC822.HEADER FLAGS)")
                raw_header = msg_data[0][1]
                flags_str  = msg_data[0][0].decode()
                msg = email.message_from_bytes(raw_header)

                messages.append({
                    "uid":     uid.decode(),
                    "subject": _decode_str(msg.get("Subject", "(제목 없음)")),
                    "from":    _decode_str(msg.get("From", "")),
                    "date":    msg.get("Date", ""),
                    "is_read": "\\Seen" in flags_str,
                })

        return messages

    def get_message(self, account_id: str, uid: str) -> dict:
        with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, ssl_context=_imap_context()) as imap:
            imap.login(f"{account_id}@{MAIL_DOMAIN}", _mail_password(account_id))
            imap.select("INBOX")
            imap.store(uid.encode(), "+FLAGS", "\\Seen")

            _, msg_data = imap.fetch(uid.encode(), "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    ct = part.get_content_type()
                    if ct == "text/plain":
                        body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                        break
                    if ct == "text/html" and not body:
                        body = part.get_payload(decode=True).decode("utf-8", errors="replace")
            else:
                body = msg.get_payload(decode=True).decode("utf-8", errors="replace")

            return {
                "uid":     uid,
                "subject": _decode_str(msg.get("Subject", "(제목 없음)")),
                "from":    _decode_str(msg.get("From", "")),
                "to":      _decode_str(msg.get("To", "")),
                "date":    msg.get("Date", ""),
                "body":    body,
            }

    def send_email(self, from_account_id: str, to: str, subject: str, body: str) -> bool:
        msg = MIMEMultipart()
        msg["From"]    = f"{from_account_id}@{MAIL_DOMAIN}"
        msg["To"]      = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.ehlo()
            smtp.starttls(context=ctx)
            smtp.login(f"{from_account_id}@{MAIL_DOMAIN}", _mail_password(from_account_id))
            smtp.sendmail(msg["From"], [to], msg.as_string())

        return True

    def delete_message(self, account_id: str, uid: str) -> bool:
        with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, ssl_context=_imap_context()) as imap:
            imap.login(f"{account_id}@{MAIL_DOMAIN}", _mail_password(account_id))
            imap.select("INBOX")
            imap.store(uid.encode(), "+FLAGS", "\\Deleted")
            imap.expunge()
        return True
