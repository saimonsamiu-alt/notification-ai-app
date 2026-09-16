"""
Email fetcher — IMAP দিয়ে সাম্প্রতিক অপঠিত মেসেজ টেনে আনে।
Gmail ব্যবহার করলে normal password কাজ করবে না — App Password লাগবে
(Google Account -> Security -> App Passwords থেকে বানাতে হবে)।
"""
import email
import imaplib
from datetime import datetime
from email.header import decode_header

from notification_agent.config import EMAIL
from notification_agent.models import Message


def _decode(value: str) -> str:
    if not value:
        return ""
    decoded, encoding = decode_header(value)[0]
    if isinstance(decoded, bytes):
        return decoded.decode(encoding or "utf-8", errors="ignore")
    return decoded


def fetch_recent_emails(limit: int = 20) -> list[Message]:
    """সাম্প্রতিক অপঠিত ইমেইল ফেরত দেয়। কোনো সমস্যা হলে খালি লিস্ট দেয়, পুরো অ্যাপ ক্র্যাশ করে না।"""
    if not EMAIL.enabled:
        return []

    messages: list[Message] = []
    try:
        imap = imaplib.IMAP4_SSL(EMAIL.host, EMAIL.port)
        imap.login(EMAIL.user, EMAIL.password)
        imap.select("INBOX")

        status, data = imap.search(None, "UNSEEN")
        if status != "OK":
            return []

        ids = data[0].split()[-limit:]  # সবচেয়ে সাম্প্রতিক কয়টা

        for msg_id in ids:
            status, msg_data = imap.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue
            raw_email = msg_data[0][1]
            parsed = email.message_from_bytes(raw_email)

            subject = _decode(parsed.get("Subject", ""))
            sender = _decode(parsed.get("From", ""))

            body = ""
            if parsed.is_multipart():
                for part in parsed.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            body = part.get_payload(decode=True).decode(errors="ignore")
                        except Exception:
                            pass
                        break
            else:
                try:
                    body = parsed.get_payload(decode=True).decode(errors="ignore")
                except Exception:
                    body = str(parsed.get_payload())

            messages.append(Message(
                source="email",
                sender=sender,
                subject=subject,
                body=body[:2000],  # খুব বড় বডি ট্রাংকেট করে রাখা, পরে LLM-এ পাঠাতে সুবিধা হবে
                received_at=datetime.now(),
                raw_id=msg_id.decode(),
            ))

        imap.logout()
    except Exception as e:
        print(f"[email_source] সমস্যা হয়েছে, ইমেইল স্কিপ করা হলো: {e}")
        return []

    return messages
