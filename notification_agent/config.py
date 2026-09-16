"""
সব সেটিংস .env ফাইল থেকে লোড হয় এখানে।
"""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class EmailConfig:
    host: str = os.getenv("EMAIL_IMAP_HOST", "imap.gmail.com")
    port: int = int(os.getenv("EMAIL_IMAP_PORT", "993"))
    user: str = os.getenv("EMAIL_USER", "")
    password: str = os.getenv("EMAIL_APP_PASSWORD", "")  # Gmail হলে App Password লাগবে, সাধারণ পাসওয়ার্ড না
    enabled: bool = bool(os.getenv("EMAIL_USER") and os.getenv("EMAIL_APP_PASSWORD"))


@dataclass
class TelegramConfig:
    bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    enabled: bool = bool(os.getenv("TELEGRAM_BOT_TOKEN"))


@dataclass
class PriorityConfig:
    # কমা দিয়ে আলাদা করা ইমেইল/ইউজারনেম যাদের মেসেজ সবসময় জরুরি ধরা হবে
    vip_senders: list = field(default_factory=lambda: [
        s.strip().lower() for s in os.getenv("VIP_SENDERS", "").split(",") if s.strip()
    ])
    # কমা দিয়ে আলাদা করা কিওয়ার্ড, যেগুলো থাকলে মেসেজ জরুরি ধরা হবে
    important_keywords: list = field(default_factory=lambda: [
        k.strip().lower() for k in os.getenv(
            "IMPORTANT_KEYWORDS",
            "urgent,asap,জরুরি,deadline,important,fund,payment,invoice"
        ).split(",") if k.strip()
    ])


EMAIL = EmailConfig()
TELEGRAM = TelegramConfig()
PRIORITY = PriorityConfig()
