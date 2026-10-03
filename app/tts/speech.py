import os
import re
import time
import asyncio
import tempfile
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
}

_ACRONYMS = {k: v for k, v in PRONUNCIATION_DICT.items() if k.isupper()}
_WORDS = {k.lower(): v for k, v in PRONUNCIATION_DICT.items() if not k.isupper()}


def _build_pattern(keys, flags=0):
    ordered = sorted(keys, key=len, reverse=True)
    return re.compile(r"(?<!\w)(" + "|".join(re.escape(k) for k in ordered) + r")(?!\w)", flags)


_ACRONYM_RE = _build_pattern(_ACRONYMS.keys())
_WORD_RE = _build_pattern(_WORDS.keys(), re.IGNORECASE)


def normalize_text_for_speech(text):
    t = text
    t = _ACRONYM_RE.sub(lambda m: _ACRONYMS[m.group(0)], t)
    t = _WORD_RE.sub(lambda m: _WORDS[m.group(0).lower()], t)
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


async def _synthesize_chunk(chunk, path, voice, rate, sem, retries=2):
    async with sem:
        for attempt in range(retries + 1):
            try:
                await edge_tts.Communicate(chunk, voice, rate=rate).save(path)
                return
            except Exception:
                if attempt == retries:
                    raise
                await asyncio.sleep(1)


def _read_bytes_with_retry(path, retries=8, delay=0.25):
    """Trên Windows, file vừa ghi xong đôi khi vẫn bị khóa trong chốc lát
    (thường do Windows Defender quét file). Thử đọc lại vài lần thay vì báo lỗi ngay."""
    last_err = None
    for attempt in range(retries):
        try:
            with open(path, "rb") as f:
                return f.read()
        except (PermissionError, OSError) as e:
            last_err = e
            time.sleep(delay)
    raise last_err


async def generate_speech_async(
    text,
    output_file="summary_audio.mp3",
    voice=VOICE,
    rate="+0%",
    max_parallel=4,
):
    if not text or not text.strip():
        text = "Lỗi. Không có nội dung để đọc."

    text = re.sub(r"[*_#`]", "", text)
    chunks = split_into_chunks(text)

    os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
    if os.path.exists(output_file):
        os.remove(output_file)

    print(f"[TTS] Tạo audio: {len(chunks)} đoạn, song song tối đa {max_parallel}...")

    with tempfile.TemporaryDirectory() as tmp:
        paths = [os.path.join(tmp, f"{i:04d}.mp3") for i in range(len(chunks))]
        sem = asyncio.Semaphore(max_parallel)
        await asyncio.gather(
            *[_synthesize_chunk(c, p, voice, rate, sem) for c, p in zip(chunks, paths)]
        )
        # Nhường một nhịp cho hệ điều hành giải phóng khóa file trước khi đọc lại
        await asyncio.sleep(0.2)

        with open(output_file, "wb") as out:
            for p in paths:
                out.write(_read_bytes_with_retry(p))

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
