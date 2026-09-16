"""
ফেজ ১: rule-based ফিল্টার — VIP sender বা keyword থাকলে "জরুরি" মার্ক করে।
ফেজ ২-তে এটা লোকাল LLM দিয়ে replace/upgrade হবে (Ollama বসানোর পর)।
"""
from notification_agent.config import PRIORITY
from notification_agent.models import Message


def classify_importance(msg: Message) -> Message:
    sender_lower = msg.sender.lower()
    text_lower = f"{msg.subject} {msg.body}".lower()

    for vip in PRIORITY.vip_senders:
        if vip in sender_lower:
            msg.is_important = True
            msg.importance_reason = f"VIP sender ({vip})"
            return msg

    for keyword in PRIORITY.important_keywords:
        if keyword in text_lower:
            msg.is_important = True
            msg.importance_reason = f"কিওয়ার্ড মিলেছে: '{keyword}'"
            return msg

    msg.is_important = False
    msg.importance_reason = "কোনো VIP/কিওয়ার্ড মিলেনি"
    return msg
