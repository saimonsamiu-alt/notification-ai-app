"""
ফেজ ৩ + সিকিউরিটি ফিচার ২: প্রতিটা মেসেজে ইউজার আসলে কী রিপ্লাই দিয়েছে,
সেটা লোকালি একটা ফাইলে জমা রাখে — data/reply_log.jsonl।

প্রতিটা এন্ট্রি আগের এন্ট্রির হ্যাশের সাথে চেইন করা থাকে (ব্লকচেইনের ধারণা থেকে নেওয়া) —
কেউ যদি পুরানো একটা এন্ট্রি চুপিচুপি বদলে দেয়, পরের সব এন্ট্রির হ্যাশ ভেঙে যাবে,
তাই verify_log_integrity() দিয়ে সহজেই ধরা পড়বে কোথায় গোলমাল হয়েছে।

এই ডেটাই পরে QLoRA দিয়ে ফাইন-টিউনিংয়ের কাজে লাগবে। সম্পূর্ণ লোকাল, কোথাও পাঠানো হয় না।
"""
import hashlib
import json
import os
from datetime import datetime

LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "reply_log.jsonl")
GENESIS_HASH = "0" * 64  # প্রথম এন্ট্রির "আগের হ্যাশ" হিসেবে ব্যবহার হয়


def _hash_entry(entry: dict) -> str:
    canonical = json.dumps(entry, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _get_last_hash() -> str:
    if not os.path.exists(LOG_PATH):
        return GENESIS_HASH
    last_hash = GENESIS_HASH
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                last_hash = json.loads(line).get("entry_hash", GENESIS_HASH)
    return last_hash


def log_reply(
    source: str,
    sender: str,
    original_message: str,
    suggested_category: str,
    suggested_reply: str,
    actual_reply: str,
) -> None:
    """একটা রিপ্লাই ইন্টারঅ্যাকশন হ্যাশ-চেইন সহ লগ করে।"""
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

    entry = {
        "timestamp": datetime.now().isoformat(),
        "source": source,
        "sender": sender,
        "original_message": original_message[:500],
        "suggested_category": suggested_category,
        "suggested_reply": suggested_reply,
        "actual_reply": actual_reply,
        "used_suggestion_as_is": actual_reply.strip() == suggested_reply.strip(),
        "prev_hash": _get_last_hash(),
    }
    entry["entry_hash"] = _hash_entry(entry)

    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[reply_logger] লগ সেভ করা যায়নি, কিন্তু অ্যাপ চলতে থাকবে: {e}")


def verify_log_integrity() -> tuple[bool, int]:
    """(is_ok, প্রথম গোলমাল যে লাইনে) ফেরত দেয়। লগ ফাইল না থাকলে ok=True।"""
    if not os.path.exists(LOG_PATH):
        return True, -1

    expected_prev = GENESIS_HASH
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            stored_hash = entry.pop("entry_hash", None)
            if entry.get("prev_hash") != expected_prev:
                return False, line_num
            if _hash_entry(entry) != stored_hash:
                return False, line_num
            expected_prev = stored_hash

    return True, -1
