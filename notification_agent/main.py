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
from notification_agent.best_picker import rank_messages_in_categories, print_rankings
from notification_agent.rubric_manager import get_or_create_rubric
from notification_agent.compare_mode import compare_messages
from notification_agent.persona_manager import get_or_create_persona, persona_guidance_text
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


def run_once(persona_text: str = "") -> list[Message]:
    all_messages: list[Message] = []
    all_messages.extend(fetch_recent_emails())
    all_messages.extend(fetch_recent_telegram())
    all_messages = [classify_with_llm(m, persona_text) for m in all_messages]
    return all_messages


_feedback_count_since_summary = 0


def _acknowledge_feedback(kind: str) -> None:
    """ইউজার সাজেশন এড়িয়ে গেলে বা বদলে দিলে উষ্ণভাবে স্বীকার করে, বিরক্তিকর না হয়ে।
    কয়েকবার হলে একটা ছোট সারাংশও দেখায় যে তোমার feedback থেকে শিখছে।"""
    global _feedback_count_since_summary
    if kind == "skip":
        print("ঠিক আছে, বুঝেছি — এটা তোমার জন্য গুরুত্বপূর্ণ না, মনে রাখলাম।")
    elif kind == "edit":
        print("বুঝেছি, তোমার নিজের ভাষায় ঠিক করে দিলে — এটাও শিখে রাখছি।")

    _feedback_count_since_summary += 1
    if _feedback_count_since_summary >= 3:
        print("\n(তোমার এই ধরনের feedback থেকে আমি ধীরে ধীরে নিজেকে ঠিক করে নিচ্ছি — "
              "আর কিছু বদলানো দরকার মনে হলে যেকোনো সময় বলো।)\n")
        _feedback_count_since_summary = 0


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
            _acknowledge_feedback("skip")
            continue

        actual_reply = choice if choice else suggested
        if choice and choice.strip() != suggested.strip():
            _acknowledge_feedback("edit")

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


def offer_compare_mode(rankings: dict, rubric: dict) -> None:
    """র‍্যাংকিং দেখানোর পর ইউজারকে compare mode ব্যবহারের সুযোগ দেয় (ঐচ্ছিক, স্কিপযোগ্য)।"""
    if not rankings:
        return
    choice = input("\nকোনো ২-৩টা মেসেজ পাশাপাশি তুলনা করে দেখতে চাও? ক্যাটাগরির নাম লিখো, না চাইলে Enter: ").strip()
    if not choice or choice not in rankings:
        return

    ranked_list = rankings[choice]
    print(f"এই ক্যাটাগরিতে: {[(i, r.message.sender) for i, r in enumerate(ranked_list)]}")
    idx_input = input("কোন কোন নম্বর তুলনা করবে (কমা দিয়ে, যেমন 0,1): ").strip()
    try:
        indices = [int(x) for x in idx_input.split(",")]
        selected = [ranked_list[i].message for i in indices if 0 <= i < len(ranked_list)]
    except ValueError:
        print("বুঝতে পারিনি, স্কিপ করা হলো।")
        return

    if len(selected) < 2:
        print("তুলনার জন্য অন্তত ২টা দরকার, স্কিপ করা হলো।")
        return

    result = compare_messages(selected, rubric)
    if result:
        print(f"\n===== তুলনা =====\n{result}\n")
    else:
        print("তুলনা করা যায়নি (Ollama চালু আছে কিনা দেখো)।")


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

    rubric = get_or_create_rubric()
    persona = get_or_create_persona()
    persona_text = persona_guidance_text(persona)

    while True:
        messages = run_once(persona_text)
        print_dashboard(messages)
        important = [m for m in messages if m.is_important]
        if important:
            rankings = rank_messages_in_categories(important, rubric)
            print_rankings(rankings)
            offer_compare_mode(rankings, rubric)
            handle_replies(important)
        print(f"\n{CHECK_INTERVAL_SECONDS} সেকেন্ড পর আবার চেক করব... (থামাতে Ctrl+C চাপো)")
        try:
            time.sleep(CHECK_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            print("থেমে গেল।")
            break


if __name__ == "__main__":
    main()
