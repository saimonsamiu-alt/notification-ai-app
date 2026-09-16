"""
ফেজ ২: লোকাল LLM (Ollama-র মাধ্যমে) দিয়ে মেসেজ ক্লাসিফাই করে —
rule-based filter-এর চেয়ে স্মার্ট, কারণ এটা মেসেজের মানে বোঝে, শুধু কিওয়ার্ড মেলায় না।

চালানোর আগে লাগবে:
1. https://ollama.com থেকে Ollama ইনস্টল করা
2. টার্মিনালে: ollama pull llama3.2:3b   (ছোট, দ্রুত মডেল — 6GB VRAM-এ আরামে চলে)
3. Ollama ব্যাকগ্রাউন্ডে চালু থাকতে হবে (ইনস্টল করলে এমনিতেই চালু থাকে)

Ollama না থাকলে বা বন্ধ থাকলে এই ফাংশন নিজে থেকেই rule-based filter-এ fallback করবে,
অ্যাপ ক্র্যাশ করবে না।
"""
import json
import requests

from notification_agent.filter import classify_importance as rule_based_classify
from notification_agent.models import Message

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:3b"
TIMEOUT_SECONDS = 15

PROMPT_TEMPLATE = """তুমি একজন সহকারী যে ঠিক করে দাও একটা মেসেজ জরুরি কিনা।
নিচের মেসেজটা পড়ো এবং শুধু এই JSON ফরম্যাটে উত্তর দাও, অন্য কিছু লিখো না:
{{"important": true অথবা false, "reason": "এক লাইনে কারণ"}}

মেসেজের বিষয়: {subject}
মেসেজের লেখক: {sender}
মেসেজের লেখা: {body}
"""


def _is_ollama_available() -> bool:
    try:
        requests.get("http://localhost:11434", timeout=2)
        return True
    except Exception:
        return False


def classify_with_llm(msg: Message) -> Message:
    """LLM দিয়ে ক্লাসিফাই করার চেষ্টা করে, সমস্যা হলে rule-based-এ fallback করে।"""
    if not _is_ollama_available():
        return rule_based_classify(msg)

    prompt = PROMPT_TEMPLATE.format(
        subject=msg.subject or "(নেই)",
        sender=msg.sender,
        body=msg.body[:800],  # প্রম্পট ছোট রাখা, দ্রুত রেসপন্সের জন্য
    )

    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": MODEL_NAME, "prompt": prompt, "stream": False, "format": "json"},
            timeout=TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        result_text = resp.json().get("response", "{}")
        parsed = json.loads(result_text)

        msg.is_important = bool(parsed.get("important", False))
        msg.importance_reason = f"[LLM] {parsed.get('reason', 'কোনো কারণ দেয়নি')}"
        return msg

    except Exception as e:
        print(f"[llm_classifier] LLM ব্যর্থ হলো, rule-based-এ ফিরে যাচ্ছি: {e}")
        return rule_based_classify(msg)
