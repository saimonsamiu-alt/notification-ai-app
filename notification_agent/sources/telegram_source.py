"""
Telegram fetcher — Bot API দিয়ে সাম্প্রতিক মেসেজ টেনে আনে।
এখানে একটা Telegram Bot বানাতে হবে @BotFather দিয়ে, আর ইউজারকে সেই বটে
নিজে থেকে মেসেজ করতে হবে (বট নিজে থেকে DM history পড়তে পারে না, এটা Telegram-এর নিয়ম)।
"""
import requests

from notification_agent.config import TELEGRAM
from notification_agent.models import Message
from datetime import datetime

API_BASE = "https://api.telegram.org/bot{token}/{method}"

_last_update_id: int | None = None


def fetch_recent_telegram(limit: int = 20) -> list[Message]:
    """সাম্প্রতিক Telegram মেসেজ ফেরত দেয়। সমস্যা হলে খালি লিস্ট দেয়, ক্র্যাশ করে না।"""
    global _last_update_id

    if not TELEGRAM.enabled:
        return []

    messages: list[Message] = []
    try:
        url = API_BASE.format(token=TELEGRAM.bot_token, method="getUpdates")
        params = {"limit": limit}
        if _last_update_id is not None:
            params["offset"] = _last_update_id + 1

        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if not data.get("ok"):
            print(f"[telegram_source] Telegram API error: {data}")
            return []

        for update in data.get("result", []):
            _last_update_id = update["update_id"]
            msg = update.get("message")
            if not msg or "text" not in msg:
                continue

            sender = msg["from"].get("username") or msg["from"].get("first_name", "unknown")

            messages.append(Message(
                source="telegram",
                sender=sender,
                subject="",
                body=msg["text"][:2000],
                received_at=datetime.fromtimestamp(msg["date"]),
                raw_id=str(msg["message_id"]),
            ))

    except Exception as e:
        print(f"[telegram_source] সমস্যা হয়েছে, Telegram স্কিপ করা হলো: {e}")
        return []

    return messages
