"""
ফেজ ৩: প্রি-সেট রিপ্লাই টেমপ্লেট।
LLM মেসেজ পড়ে বুঝবে কোন ক্যাটাগরিতে পড়ে, সেই অনুযায়ী একটা টেমপ্লেট সাজেস্ট করবে।
ইউজার সেটা হুবহু পাঠাতে পারে, এডিট করতে পারে, বা পুরো নতুন লিখতে পারে —
তিনটার প্রতিটাই লগ হবে reply_logger.py-তে, পরে ফাইন-টিউনিংয়ের ডেটা হিসেবে কাজে লাগবে।
"""

TEMPLATES = {
    "meeting_request": "ধন্যবাদ! আমি একটু ব্যস্ত আছি, {time}-এর মধ্যে কনফার্ম করে জানাচ্ছি।",
    "busy_acknowledge": "মেসেজ পেয়েছি, এখন মিটিং-এ আছি, একটু পরে বিস্তারিত রিপ্লাই দিচ্ছি।",
    "fund_request": "আপনার প্রস্তাবটা দেখেছি, বিস্তারিত রিভিউ করে {time}-এর মধ্যে জানাবো।",
    "general_ack": "মেসেজ পেয়েছি, দেখে জানাচ্ছি।",
    "deadline_related": "খেয়াল আছে, নির্ধারিত সময়ের মধ্যে করে দেবো।",
}

# কোন কিওয়ার্ড দেখলে কোন টেমপ্লেট সাজেস্ট করবে (ফেজ ২-এর LLM ক্লাসিফায়ার এটাকে
# আরও স্মার্ট করে দেবে ভবিষ্যতে, এখন শুরুর জন্য rule-based ম্যাপিং)
CATEGORY_KEYWORDS = {
    "meeting_request": ["meeting", "দেখা করতে", "মিট", "কল করব"],
    "fund_request": ["fund", "টাকা", "payment", "invoice", "donation"],
    "deadline_related": ["deadline", "সময়সীমা", "due date"],
}


def suggest_reply(msg_body: str, msg_subject: str = "") -> tuple[str, str]:
    """মেসেজ দেখে (category, suggested_reply_template) ফেরত দেয়।"""
    text = f"{msg_subject} {msg_body}".lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text:
                return category, TEMPLATES[category]

    return "general_ack", TEMPLATES["general_ack"]
