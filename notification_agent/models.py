"""
সব সোর্স (Email, Telegram, ভবিষ্যতে আরও) থেকে আসা মেসেজ এই একই ফরম্যাটে আসবে,
যাতে ফিল্টার/দ্যাশবোর্ড লজিক প্ল্যাটফর্ম-অ্যাগনস্টিক থাকে।
"""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Message:
    source: str          # "email" | "telegram"
    sender: str           # ইমেইল অ্যাড্রেস বা টেলিগ্রাম ইউজারনেম
    subject: str           # ইমেইলের subject, টেলিগ্রামের জন্য খালি থাকতে পারে
    body: str
    received_at: datetime
    raw_id: str            # সোর্সের নিজস্ব আইডি (dedupe করার জন্য)
    is_important: bool = False
    importance_reason: str = ""
