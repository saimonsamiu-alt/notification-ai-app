"""
সিকিউরিটি ফিচার ৩: অ্যানোমালি ডিটেকশন / রেট-লিমিট।

হঠাৎ অস্বাভাবিক পরিমাণ অটো-অ্যাকশন (যেমন এক মিনিটে অনেকগুলো রিপ্লাই পাঠানো) হলে
এটা "safe mode"-এ চলে যায় — বাকি সব auto-action বন্ধ, ম্যানুয়াল অনুমোদন লাগবে আবার চালু হতে।

এটা defense-in-depth-এর অংশ — কোড ইন্টেগ্রিটি চেক পাস করলেও (মানে কোড বদলায়নি),
যদি কোনো bug বা অপ্রত্যাশিত অবস্থার কারণে অ্যাপ অস্বাভাবিক আচরণ শুরু করে, তাহলেও এটা ধরবে।
"""
import time

MAX_ACTIONS_PER_WINDOW = 5      # এই সংখ্যার বেশি হলে সন্দেহজনক
WINDOW_SECONDS = 60


class SafetyMonitor:
    def __init__(self) -> None:
        self._action_timestamps: list[float] = []
        self.safe_mode: bool = False
        self.safe_mode_reason: str = ""

    def record_action(self, action_name: str) -> None:
        """প্রতিটা sensitive action (reply পাঠানো, কল হ্যান্ডলিং ইত্যাদি) কল করার আগে এটা ডাকতে হবে।"""
        now = time.time()
        self._action_timestamps = [t for t in self._action_timestamps if now - t < WINDOW_SECONDS]
        self._action_timestamps.append(now)

        if len(self._action_timestamps) > MAX_ACTIONS_PER_WINDOW:
            self.safe_mode = True
            self.safe_mode_reason = (
                f"{WINDOW_SECONDS} সেকেন্ডে {len(self._action_timestamps)}টা '{action_name}' অ্যাকশন হয়েছে, "
                f"যা স্বাভাবিক সীমার (max {MAX_ACTIONS_PER_WINDOW}) বাইরে।"
            )

    def check(self) -> bool:
        """True মানে সব স্বাভাবিক, False মানে safe mode চালু হয়ে গেছে।"""
        return not self.safe_mode

    def reset(self) -> None:
        """ইউজার ম্যানুয়ালি রিভিউ করে ঠিক আছে মনে করলে এটা কল করে safe mode থেকে বের হওয়া যায়।"""
        self.safe_mode = False
        self.safe_mode_reason = ""
        self._action_timestamps = []


# পুরো অ্যাপের জন্য একটাই shared instance
monitor = SafetyMonitor()
