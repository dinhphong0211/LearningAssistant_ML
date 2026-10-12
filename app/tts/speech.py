import os
import re
import asyncio
import random
from functools import lru_cache

import edge_tts

VOICE = "vi-VN-HoaiMyNeural"

PRONUNCIATION_DICT = {
    "API": "ây pi ai",
    "Laravel": "la ra veo",
    "Artisan": "a ti sần",
    "Controller": "cần trôn lơ",
    "PHP": "pê hát pê",
    "URL": "u rờ lờ",
    "VS Code": "vi ét cốt",
    "Terminal": "tơ mi nồ",
    "Product": "prô đắc",
    "AI": "ây ai",
    "Machine Learning": "mơ xin lơn ninh",
    "Scrum": "sờ cờ râm",
    "Agile": "a giai",
    "NLP": "en eo pi",
    "CNN": "xi en en",
    "RNN": "a en en",
    "LSTM": "eo ét ti em",
    "GPU": "gi pi iu",
    "SQLite" : "ét qui lai",
    "PostgreSQL": "pốt rơ ét qui eo",
}

# Bổ sung (phiên âm xấp xỉ, cần NGHE THỬ và chỉnh lại từ nào đọc chưa chuẩn).
# Từ in hoa toàn bộ được khớp phân biệt hoa/thường; các từ còn lại không phân biệt.
EXTRA_PRONUNCIATION = {
    # viết tắt
    "BERT": "bơt", "GPT": "gi pi ti", "SVM": "ét vi em", "MLP": "em eo pi", "KNN": "ca en en",
    "PCA": "pi xi ây", "SGD": "ét gi đi", "MSE": "em ét i", "AUC": "ây iu xi", "ROC": "a ô xi",
    "ROUGE": "ru giơ", "TF-IDF": "ti ép ai đi ép", "LLM": "eo eo em", "OCR": "ô xi a",
    "TTS": "ti ti ét", "PDF": "pi đi ép", "SQL": "ét kiu eo", "HTML": "hát ti em eo",
    "CSS": "xi ét ét", "JSON": "gây sơn", "HTTP": "hát ti ti pi", "TCP": "ti xi pi",
    "CPU": "xi pi iu", "OOP": "ô ô pi", "ML": "em eo", "DL": "đi eo",
    # từ thường
    "overfitting": "ô vơ phít ting", "underfitting": "ân đơ phít ting",
    "gradient descent": "gờ rây đi ần đi xen", "gradient": "gờ rây đi ần",
    "dropout": "đrốp aot", "softmax": "sóp mác", "sigmoid": "xích moi", "relu": "rê lu",
    "epoch": "i pốc", "batch normalization": "bát noọc ma li zây sần", "batch": "bát",
    "backpropagation": "bác prô pa gây sần", "transformer": "tran phọc mơ",
    "attention": "ơ ten sần", "embedding": "em bét đinh", "tokenization": "tô ken ai zây sần",
    "token": "tô ken", "word2vec": "quớt tu béc", "dataset": "đa ta xét",
    "deep learning": "đíp lơn ninh", "learning rate": "lơn ninh rết",
    "neural network": "niu rồ nét quớc", "feature": "phi chơ", "regression": "ri gre sần",
    "classification": "clát xi phi kây sần", "cross-entropy": "crót en trô pi",
    "cross-validation": "crót va li đây sần", "fine-tuning": "phai tiu ninh",
    "inference": "in phơ rần", "prompt": "prôm", "python": "pai thơn", "java": "gia va",
    "javascript": "gia va xcờ ríp", "docker": "đóc cơ", "github": "ghít hắp", "git": "ghít",
    "framework": "phrêm quớc", "database": "đa ta bêi", "server": "xơ vơ", "frontend": "phrần en",
    "backend": "béc en", "debug": "đi bấc", "algorithm": "an gô ri thừm", "quiz": "quít",
    "streamlit": "xờ trim lít", "gemini": "giem mi nai", "accuracy": "ác kiu ra xi",
    "precision": "pri xi giần", "recall": "ri cồ", "validation": "va li đây sần",
}
PRONUNCIATION_DICT.update(EXTRA_PRONUNCIATION)

# Ghi đè riêng từng giọng nếu nghe thử thấy lệch (mặc định để trống: dùng chung bảng trên).
# Ví dụ: VOICE_OVERRIDES["vi-VN-NamMinhNeural"] = {"epoch": "ê pốc"}
VOICE_OVERRIDES = {
    "vi-VN-HoaiMyNeural": {},
    "vi-VN-NamMinhNeural": {},
}

# Số kèm đơn vị: đọc thành lời để máy khỏi đọc "GB" thành "gờ bê"
_UNIT_SPOKEN = {
    "%": "phần trăm", "GB": "ghi ga bai", "MB": "mê ga bai", "KB": "ki lô bai",
    "TB": "tê ra bai", "GHz": "ghi ga héc", "MHz": "mê ga héc",
    "ms": "mi li giây", "°C": "độ xê", "px": "pích xeo",
}
_UNIT_NUM = re.compile(r"(\d+(?:[.,]\d+)?)\s?(%|GB|MB|KB|TB|GHz|MHz|ms|°C|px)(?![A-Za-z])")


def _build_pattern(keys, flags=0):
    ordered = sorted(keys, key=len, reverse=True)
    return re.compile(r"(?<!\w)(" + "|".join(re.escape(k) for k in ordered) + r")(?!\w)", flags)


@lru_cache(maxsize=8)
def _tables(voice):
    merged = {**PRONUNCIATION_DICT, **VOICE_OVERRIDES.get(voice, {})}
    acronyms = {k: v for k, v in merged.items() if k.isupper()}
    words = {k.lower(): v for k, v in merged.items() if not k.isupper()}
    return acronyms, words, _build_pattern(acronyms.keys()), _build_pattern(words.keys(), re.IGNORECASE)


def normalize_text_for_speech(text, voice=VOICE):
    """Viết lại văn bản cho máy đọc. Độc lập với giọng, trừ giọng đa ngôn ngữ (đọc tiếng Anh tự nhiên
    nên không áp phiên âm kiểu Việt)."""
    t = text
    t = _UNIT_NUM.sub(lambda m: f"{m.group(1)} {_UNIT_SPOKEN[m.group(2)]}", t)
    if "Multilingual" not in (voice or ""):
        acronyms, words, acr_re, word_re = _tables(voice)
        t = acr_re.sub(lambda m: acronyms[m.group(0)], t)
        t = word_re.sub(lambda m: words[m.group(0).lower()], t)
    t = t.replace(":", ", ")
    t = t.replace("/", " xuyệt ")
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"\n+", ". ", t)
    t = re.sub(r"(\.\s*){2,}", ". ", t)
    return t.strip()


def split_into_chunks(text, max_chars=700):
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks, current = [], ""
    for s in sentences:
        if len(current) + len(s) + 1 <= max_chars:
            current = f"{current} {s}".strip()
            continue
        if current:
            chunks.append(current)
        while len(s) > max_chars:
            cut = s.rfind(" ", 0, max_chars)
            if cut <= 0:
                cut = max_chars
            chunks.append(s[:cut].strip())
            s = s[cut:].strip()
        current = s
    if current:
        chunks.append(current)
    return [c for c in chunks if c.strip()]


async def _synthesize_chunk(chunk, voice, rate, sem, retries=4):
    """Trả về bytes mp3 của một đoạn, nhận thẳng từ luồng stream() của edge-tts.
    Không ghi file tạm nên không dính lỗi WinError 32 (Windows Defender khóa file)."""
    async with sem:
        for attempt in range(retries + 1):
            try:
                buf = bytearray()
                async for msg in edge_tts.Communicate(chunk, voice, rate=rate).stream():
                    if msg["type"] == "audio":
                        buf += msg["data"]
                if not buf:
                    raise RuntimeError("Dịch vụ giọng nói không trả về dữ liệu âm thanh.")
                return bytes(buf)
            except Exception:
                if attempt == retries:
                    raise
                # Lùi dần (1.5s, 3s, 6s, 12s) + chút ngẫu nhiên: dịch vụ Edge đôi khi từ chối
                # (403/ngắt kết nối) khi nhiều kết nối mở liên tiếp, đợi một nhịp thường qua được.
                await asyncio.sleep(1.5 * (2 ** attempt) + random.random())


async def generate_speech_bytes_async(text, voice=VOICE, rate="+0%", max_parallel=4):
    """Tạo audio hoàn toàn trong bộ nhớ, trả về bytes mp3 (các đoạn nối theo thứ tự)."""
    if not text or not text.strip():
        text = "Lỗi. Không có nội dung để đọc."
    text = re.sub(r"[*_#`]", "", text)
    chunks = split_into_chunks(text)
    print(f"[TTS] Tạo audio: {len(chunks)} đoạn, song song tối đa {max_parallel}...")
    sem = asyncio.Semaphore(max_parallel)
    parts = await asyncio.gather(*[_synthesize_chunk(c, voice, rate, sem) for c in chunks])
    return b"".join(parts)


async def generate_speech_async(text, output_file="summary_audio.mp3", voice=VOICE, rate="+0%", max_parallel=4):
    """Giữ lại để tương thích: tạo audio rồi ghi ra output_file."""
    data = await generate_speech_bytes_async(text, voice, rate, max_parallel)
    os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
    with open(output_file, "wb") as f:
        f.write(data)
    return output_file


# ---------------- Danh sách giọng đọc ----------------
DEFAULT_VOICE_OPTIONS = {
    "Hoài My (nữ, vi-VN)": "vi-VN-HoaiMyNeural",
    "Nam Minh (nam, vi-VN)": "vi-VN-NamMinhNeural",
}


def fetch_voice_options(include_multilingual=False):
    """Lấy danh sách giọng từ dịch vụ Edge TTS. Giọng tiếng Việt luôn đứng đầu.
    Nếu không có mạng thì dùng danh sách mặc định (2 giọng Việt)."""
    try:
        voices = asyncio.run(edge_tts.list_voices())
    except Exception:
        return dict(DEFAULT_VOICE_OPTIONS)

    gender = {"Female": "nữ", "Male": "nam"}
    vi, multi = {}, {}
    for v in voices:
        short = v.get("ShortName", "")
        label_name = short.split("-", 2)[-1].replace("Neural", "")
        label = f"{label_name} ({gender.get(v.get('Gender'), v.get('Gender', ''))}, {v.get('Locale', '')})"
        if v.get("Locale", "").startswith("vi-"):
            vi[label] = short
        elif include_multilingual and "Multilingual" in short:
            multi[f"{label} - đa ngôn ngữ, thử nghiệm"] = short
    return {**(vi or DEFAULT_VOICE_OPTIONS), **multi}