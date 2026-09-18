"""
ইউজার কোন ধরনের (স্টুডেন্ট/বিজনেস/অফিশিয়াল) সেটা একবার জিজ্ঞেস করে সেভ রাখে —
এর ভিত্তিতে "কী জরুরি" তার বিচার বদলায় (LLM প্রম্পটে যুক্ত হয়), যাতে সবার জন্য একই জেনেরিক
সাজেশন না দিয়ে যার যার প্রয়োজন অনুযায়ী দেখায়।
"""
import json
import os

PERSONA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "persona.json")

PERSONA_GUIDANCE = {
    "student": (
        "ইউজার একজন স্টুডেন্ট, ফোন/সোশ্যাল মিডিয়া অ্যাডিকশন কমিয়ে পড়াশোনায় ফোকাস করতে চায়। "
        "একাডেমিক ডেডলাইন, অ্যাসাইনমেন্ট, পরীক্ষা, শিক্ষকের মেসেজ — এগুলো জরুরি। "
        "সোশ্যাল মিডিয়া FOMO নোটিফিকেশন, গ্রুপ চ্যাটের গল্পগুজব — এগুলো সাধারণত জরুরি না।"
    ),
    "business": (
        "ইউজার একজন ব্যস্ত বিজনেস পার্সন, গুরুত্বপূর্ণ জিনিস মিস করতে চায় না। "
        "ক্লায়েন্ট/পার্টনারের মেসেজ, পেমেন্ট, মিটিং, ডেডলাইন — এগুলো জরুরি। "
        "সাধারণ প্রোমোশনাল/মার্কেটিং মেসেজ জরুরি না।"
    ),
    "official": (
        "ইউজার একজন অফিশিয়াল/প্রশাসনিক পদে আছে, হ্যাসেল ছাড়া আপ-টু-ডেট থাকতে চায়। "
        "নীতিগত আপডেট, অনুমোদনের অনুরোধ, জরুরি প্রশাসনিক মেসেজ — এগুলো জরুরি। "
        "রুটিন তথ্যমূলক নোটিফিকেশন কম জরুরি।"
    ),
}


def load_persona() -> str | None:
    if not os.path.exists(PERSONA_PATH):
        return None
    try:
        with open(PERSONA_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("persona")
    except Exception:
        return None


def save_persona(persona: str) -> None:
    os.makedirs(os.path.dirname(PERSONA_PATH), exist_ok=True)
    with open(PERSONA_PATH, "w", encoding="utf-8") as f:
        json.dump({"persona": persona}, f, ensure_ascii=False, indent=2)


def setup_persona_interactive() -> str:
    print("\n--- একটা ছোট প্রশ্ন (একবারই জিজ্ঞেস করব) ---")
    print("1. স্টুডেন্ট   2. বিজনেস পার্সন   3. অফিশিয়াল")
    choice = input("তুমি কোনটার সাথে বেশি মেলে (1/2/3, Enter দিলে সাধারণ থাকবে): ").strip()
    mapping = {"1": "student", "2": "business", "3": "official"}
    persona = mapping.get(choice, "general")
    save_persona(persona)
    print("ঠিক আছে, মনে রাখলাম।\n")
    return persona


def get_or_create_persona() -> str:
    existing = load_persona()
    if existing:
        return existing
    return setup_persona_interactive()


def persona_guidance_text(persona: str) -> str:
    return PERSONA_GUIDANCE.get(persona, "")
