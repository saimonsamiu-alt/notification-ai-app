"""
ফেজ ১ এর মূল এন্ট্রি পয়েন্ট।
চালানোর নিয়ম: python -m notification_agent.main
"""
import time

from notification_agent.config import EMAIL, TELEGRAM
from notification_agent.llm_classifier import classify_with_llm
from notification_agent.models import Message
from notification_agent.reply_templates import suggest_reply
from notification_agent.reply_logger import log_reply
from notification_agent.integrity_check import verify_integrity
from notification_agent.safety_monitor import monitor
from notification_agent.sources.email_source import fetch_recent_emails
from notification_agent.sources.telegram_source import fetch_recent_telegram

CHECK_INTERVAL_SECONDS = 60


def print_dashboard(messages: list[Message]) -> None:
    if not messages:
        print("কোনো নতুন মেসেজ নেই।")
        return

    important = [m for m in messages if m.is_important]
    others = [m for m in messages if not m.is_important]

    print(f"\n===== {len(important)}টা জরুরি মেসেজ =====")
    for m in important:
        title = m.subject if m.source == "email" else "(Telegram)"
        print(f"[{m.source}] {m.sender} — {title}")
        print(f"  কারণ: {m.importance_reason}")
        print(f"  {m.body[:120]}...\n")

    if others:
        print(f"===== বাকি {len(others)}টা মেসেজ (গুরুত্বপূর্ণ না) =====")
        for m in others:
            title = m.subject if m.source == "email" else "(Telegram)"
            print(f"[{m.source}] {m.sender} — {title}")


def run_once() -> list[Message]:
    all_messages: list[Message] = []
    all_messages.extend(fetch_recent_emails())
    all_messages.extend(fetch_recent_telegram())
    all_messages = [classify_with_llm(m) for m in all_messages]
    return all_messages


def handle_replies(important_messages: list[Message]) -> None:
    """জরুরি মেসেজগুলোর জন্য রিপ্লাই সাজেস্ট করে, ইউজার চাইলে reply দেয়, সব লগ হয়ে যায় (ফাইন-টিউনিং ডেটা)।"""
    if not monitor.check():
        print(f"\n⚠ SAFE MODE চালু আছে: {monitor.safe_mode_reason}")
        print("  auto-reply বন্ধ আছে যতক্ষণ না তুমি নিজে রিভিউ করে চালু করো (main.py-তে monitor.reset() কল করে)।")
        return

    for m in important_messages:
        category, suggested = suggest_reply(m.body, m.subject)
        print(f"\n--- রিপ্লাই দেবে? [{m.source}] {m.sender} ---")
        print(f"সাজেস্টেড রিপ্লাই ({category}): {suggested}")
        choice = input("Enter চাপো সাজেস্টেড রিপ্লাই পাঠাতে, নিজের রিপ্লাই লিখতে পারো, অথবা 'skip' লিখো: ").strip()

        if choice.lower() == "skip":
            continue

        actual_reply = choice if choice else suggested
        monitor.record_action("reply")
        if not monitor.check():
            print(f"\n⚠ SAFE MODE চালু হয়ে গেছে: {monitor.safe_mode_reason}")
            print("  বাকি রিপ্লাইগুলো এই রাউন্ডে থেমে যাচ্ছে, নিরাপত্তার জন্য।")
            break

        # এখানে এখনো আসল প্ল্যাটফর্মে (Email/Telegram) পাঠানোর কোড নেই — এটা ফেজ ৪-এ যোগ হবে।
        # আপাতত শুধু লগ করছি, যাতে ইউজারের রিপ্লাই-স্টাইলের ডেটা জমতে শুরু করে।
        log_reply(
            source=m.source,
            sender=m.sender,
            original_message=m.body,
            suggested_category=category,
            suggested_reply=suggested,
            actual_reply=actual_reply,
        )
        print(f"লগ হলো (এখনো সত্যিকারের প্ল্যাটফর্মে পাঠানো হয়নি, সেটা পরের ফেজে যোগ হবে): {actual_reply}")


def main() -> None:
    print("নোটিফিকেশন এজেন্ট চালু হচ্ছে...")

    integrity_ok, bad_files = verify_integrity()
    if not integrity_ok:
        print(f"  🛑 কোড ইন্টেগ্রিটি চেক ফেইল! এই ফাইলগুলো manifest-এর সাথে মিলছে না: {bad_files}")
        print("  নিরাপত্তার জন্য auto-reply বন্ধ রাখা হচ্ছে (safe mode)। নিজে বদলেছ হলে")
        print("  'python -m notification_agent.integrity_check --generate' চালিয়ে নতুন manifest বানাও।")
        monitor.safe_mode = True
        monitor.safe_mode_reason = "কোড ইন্টেগ্রিটি চেক ফেইল করেছে।"

    if not EMAIL.enabled:
        print("  ⚠ Email কনফিগার করা নেই (.env দেখো) — Email স্কিপ করা হবে।")
    if not TELEGRAM.enabled:
        print("  ⚠ Telegram কনফিগার করা নেই (.env দেখো) — Telegram স্কিপ করা হবে।")
    print("  (Ollama চালু থাকলে LLM দিয়ে ক্লাসিফাই হবে, না থাকলে rule-based filter ব্যবহার হবে)")

    while True:
        messages = run_once()
        print_dashboard(messages)
        important = [m for m in messages if m.is_important]
        if important:
            handle_replies(important)
        print(f"\n{CHECK_INTERVAL_SECONDS} সেকেন্ড পর আবার চেক করব... (থামাতে Ctrl+C চাপো)")
        try:
            time.sleep(CHECK_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            print("থেমে গেল।")
            break


if __name__ == "__main__":
    main()
