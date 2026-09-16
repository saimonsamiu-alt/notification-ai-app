"""
সিকিউরিটি ফিচার ১: কোড ইন্টেগ্রিটি চেক।

প্রথমবার `python -m notification_agent.integrity_check --generate` চালিয়ে
একটা manifest.json বানাতে হবে (সব .py ফাইলের SHA-256 হ্যাশ সেভ থাকে)।

এরপর থেকে অ্যাপ চালু হওয়ার সময় স্বয়ংক্রিয়ভাবে সব ফাইল আবার হ্যাশ করে মিলিয়ে দেখে।
কোনো ফাইল বদলে গেলে (ম্যালওয়্যার হোক বা ভুলবশত এডিট) সেটা ধরা পড়ে যাবে,
আর অ্যাপ তখন "safe mode"-এ চলে যাবে (auto-reply/call handling বন্ধ থাকবে)।

নতুন legitimate কোড আপডেট করার পর অবশ্যই আবার --generate চালিয়ে manifest রিফ্রেশ করতে হবে,
নাহলে নিজের নতুন কোডকেই "corrupted" ভাববে।
"""
import hashlib
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST_PATH = os.path.join(PROJECT_ROOT, "integrity_manifest.json")
CODE_DIR = os.path.join(PROJECT_ROOT, "notification_agent")


def _hash_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def _all_code_files() -> list[str]:
    files = []
    for root, _, filenames in os.walk(CODE_DIR):
        for fn in filenames:
            if fn.endswith(".py"):
                files.append(os.path.relpath(os.path.join(root, fn), PROJECT_ROOT))
    return sorted(files)


def generate_manifest() -> None:
    """বর্তমান কোডের হ্যাশ সেভ করে — নতুন legitimate কোড পরিবর্তনের পর এটা চালাতে হবে।"""
    manifest = {}
    for rel_path in _all_code_files():
        manifest[rel_path] = _hash_file(os.path.join(PROJECT_ROOT, rel_path))

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"[integrity_check] {len(manifest)}টা ফাইলের হ্যাশ manifest-এ সেভ হলো: {MANIFEST_PATH}")


def verify_integrity() -> tuple[bool, list[str]]:
    """
    (is_ok, mismatched_files) ফেরত দেয়।
    manifest ফাইল না থাকলে — প্রথমবার চালানো হচ্ছে ধরে নিয়ে ok=True দেয়, কিন্তু ওয়ার্নিং দেখায়।
    """
    if not os.path.exists(MANIFEST_PATH):
        print("[integrity_check] ⚠ কোনো manifest পাওয়া যায়নি — 'python -m notification_agent.integrity_check --generate' চালাও প্রথমে।")
        return True, []

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    mismatched = []
    current_files = set(_all_code_files())
    manifest_files = set(manifest.keys())

    for rel_path in manifest_files:
        full_path = os.path.join(PROJECT_ROOT, rel_path)
        if not os.path.exists(full_path):
            mismatched.append(f"{rel_path} (ফাইলটা মিসিং!)")
            continue
        if _hash_file(full_path) != manifest[rel_path]:
            mismatched.append(rel_path)

    # নতুন ফাইল যোগ হয়েছে যেটা manifest-এ নেই — এটা ক্ষতিকর নাও হতে পারে (legitimate নতুন ফিচার),
    # কিন্তু জানিয়ে রাখা ভালো
    new_files = current_files - manifest_files
    if new_files:
        print(f"[integrity_check] নতুন ফাইল পাওয়া গেছে (manifest-এ নেই): {sorted(new_files)}")

    return len(mismatched) == 0, mismatched


if __name__ == "__main__":
    if "--generate" in sys.argv:
        generate_manifest()
    else:
        ok, bad_files = verify_integrity()
        if ok:
            print("[integrity_check] সব ঠিক আছে, কোনো পরিবর্তন ধরা পড়েনি।")
        else:
            print(f"[integrity_check] ⚠ এই ফাইলগুলো বদলে গেছে: {bad_files}")
