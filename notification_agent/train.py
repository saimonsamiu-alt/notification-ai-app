"""
ফেজ ৩-এর বাকি অংশ: reply_log.jsonl-এর ডেটা দিয়ে একটা ছোট লোকাল মডেল QLoRA দিয়ে ফাইন-টিউন করে,
যাতে সেটা তোমার নিজের রিপ্লাই-স্টাইল শিখে যায়।

⚠ গুরুত্বপূর্ণ সতর্কতা: এই স্ক্রিপ্টটা GPU ছাড়া চালানো যাবে না, আর এটা এখনো তোমার আসল হার্ডওয়্যারে
টেস্ট করা হয়নি (এই কথোপকথনের environment-এ GPU/ইন্টারনেট নেই)। প্রথমবার চালানোর সময় কোনো এরর এলে
আমাকে জানিও, ঠিক করে দেব — এটাই এই প্রজেক্টের প্রথম "আনটেস্টেড" অংশ।

চালানোর আগে:
1. python -m pip install -r requirements-training.txt   (৫-১৫ মিনিট লাগতে পারে, বড় ডাউনলোড)
2. নিশ্চিত হও data/reply_log.jsonl-এ কমপক্ষে ৫০টা এন্ট্রি আছে (নিচের --check দিয়ে চেক করা যায়)

চালানোর নিয়ম:
    শুধু ডেটা কতটা জমেছে দেখতে: python -m notification_agent.train --check
    আসল ট্রেনিং শুরু করতে:      python -m notification_agent.train
"""
import json
import os
import sys

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "reply_log.jsonl")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "fine_tuned_model")
MIN_EXAMPLES = 50
BASE_MODEL = "unsloth/Llama-3.2-3B-Instruct-bnb-4bit"  # RTX 4050 (6GB)-এর জন্য উপযুক্ত সাইজ


def load_training_entries() -> list[dict]:
    if not os.path.exists(DATA_PATH):
        return []
    entries = []
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def check_data() -> None:
    entries = load_training_entries()
    print(f"এখন পর্যন্ত {len(entries)}টা রিপ্লাই লগ হয়েছে (দরকার কমপক্ষে {MIN_EXAMPLES}টা)।")
    if len(entries) < MIN_EXAMPLES:
        print(f"আরও {MIN_EXAMPLES - len(entries)}টা দরকার — অ্যাপ ব্যবহার চালিয়ে যাও, ট্রেনিং এখনই শুরু করা যাবে না।")
    else:
        print("যথেষ্ট ডেটা জমে গেছে! `python -m notification_agent.train` চালিয়ে ট্রেনিং শুরু করতে পারো।")


def format_for_training(entries: list[dict]) -> list[dict]:
    formatted = []
    for e in entries:
        instruction = (
            f"নিচের মেসেজের একটা যথাযথ রিপ্লাই লিখো।\n\n"
            f"প্রেরক: {e.get('sender', '')}\n"
            f"মেসেজ: {e.get('original_message', '')}"
        )
        output = e.get("actual_reply", "")
        if instruction and output:
            formatted.append({"instruction": instruction, "output": output})
    return formatted


def run_training() -> None:
    entries = load_training_entries()
    if len(entries) < MIN_EXAMPLES:
        print(f"যথেষ্ট ডেটা নেই ({len(entries)}/{MIN_EXAMPLES})। আগে `--check` দিয়ে দেখো, আরও ব্যবহার করে ডেটা জমাও।")
        return

    try:
        from unsloth import FastLanguageModel, is_bf16_supported
        from trl import SFTTrainer
        from transformers import TrainingArguments
        from datasets import Dataset
    except ImportError:
        print("ট্রেনিং লাইব্রেরি ইনস্টল করা নেই। আগে চালাও:")
        print("  python -m pip install -r requirements-training.txt")
        return

    print(f"{len(entries)}টা উদাহরণ দিয়ে ট্রেনিং শুরু হচ্ছে — মডেল লোড হচ্ছে (প্রথমবার কিছুক্ষণ সময় নেবে)...")

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=BASE_MODEL,
        max_seq_length=2048,
        dtype=None,
        load_in_4bit=True,
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_alpha=16,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    formatted = format_for_training(entries)

    def to_text(example: dict) -> dict:
        return {"text": f"### নির্দেশ:\n{example['instruction']}\n\n### উত্তর:\n{example['output']}"}

    dataset = Dataset.from_list(formatted).map(to_text)

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=2048,
        args=TrainingArguments(
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            warmup_steps=5,
            num_train_epochs=3,
            learning_rate=2e-4,
            fp16=not is_bf16_supported(),
            bf16=is_bf16_supported(),
            logging_steps=1,
            output_dir=OUTPUT_DIR,
            optim="adamw_8bit",
            save_strategy="no",
        ),
    )

    trainer.train()

    print("ট্রেনিং শেষ, GGUF ফরম্যাটে সেভ হচ্ছে (Ollama-তে ব্যবহারের জন্য)...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    model.save_pretrained_gguf(OUTPUT_DIR, tokenizer, quantization_method="q4_k_m")

    print(f"\nহয়ে গেছে! ফাইল আছে এখানে: {OUTPUT_DIR}")
    print("এখন Ollama-তে বসাতে এই Modelfile কমান্ডটা চালাও (নিচের নির্দেশনা দেখো)।")
    print_ollama_instructions()


def print_ollama_instructions() -> None:
    modelfile_path = os.path.join(OUTPUT_DIR, "Modelfile")
    gguf_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".gguf")] if os.path.isdir(OUTPUT_DIR) else []
    gguf_name = gguf_files[0] if gguf_files else "<তোমার-gguf-ফাইলের-নাম>"

    modelfile_content = f"FROM ./{gguf_name}\n"
    try:
        with open(modelfile_path, "w", encoding="utf-8") as f:
            f.write(modelfile_content)
        print(f"একটা Modelfile বানিয়ে দিলাম: {modelfile_path}")
    except Exception:
        pass

    print("\nটার্মিনালে এই কমান্ডগুলো চালাও:")
    print(f"  cd {OUTPUT_DIR}")
    print(f"  ollama create my-notification-model -f Modelfile")
    print("তারপর llm_classifier.py-এর MODEL_NAME বদলে 'my-notification-model' করে দাও —")
    print("এবার Ollama তোমার নিজের শেখা মডেল ব্যবহার করবে।")


if __name__ == "__main__":
    if "--check" in sys.argv:
        check_data()
    else:
        run_training()
