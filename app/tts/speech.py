import os
import re
import asyncio
import tempfile
import edge_tts

VOICE = "vi-VN-HoaiMyNeural"

# 1. TỪ ĐIỂN CHUẨN HÓA PHÁT ÂM
# Phiên âm bên dưới chỉ là gợi ý, cần nghe thử và chỉnh lại cho tự nhiên.
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
    # Thuật ngữ cho đề tài ML/NLP (gợi ý, cần kiểm chứng bằng cách nghe)
    "NLP": "en eo pi",
    "CNN": "xi en en",
    "RNN": "a en en",
    "LSTM": "eo ét ti em",
    "GPU": "gi pi iu",
}

# Từ viết tắt in hoa: chỉ khớp đúng chữ hoa (tránh nhầm với từ "ai" tiếng Việt)
_ACRONYMS = {k: v for k, v in PRONUNCIATION_DICT.items() if k.isupper()}
# Cụm từ còn lại: không phân biệt hoa/thường
_WORDS = {k.lower(): v for k, v in PRONUNCIATION_DICT.items() if not k.isupper()}


def _build_pattern(keys, flags=0):
    ordered = sorted(keys, key=len, reverse=True)  # cụm dài khớp trước
    return re.compile(r"(?<!\w)(" + "|".join(re.escape(k) for k in ordered) + r")(?!\w)", flags)


_ACRONYM_RE = _build_pattern(_ACRONYMS.keys())
_WORD_RE = _build_pattern(_WORDS.keys(), re.IGNORECASE)


def normalize_text_for_speech(text):
    """Chuẩn hóa phát âm và làm sạch văn bản trước khi đưa vào TTS."""
    t = text

    # Mỗi lượt thay chỉ chạy một lần nên kết quả không bị thay lần hai
    t = _ACRONYM_RE.sub(lambda m: _ACRONYMS[m.group(0)], t)
    t = _WORD_RE.sub(lambda m: _WORDS[m.group(0).lower()], t)

    t = t.replace(":", ", ")
    t = t.replace("/", " xuyệt ")

    t = re.sub(r"<[^>]+>", "", t)            # bỏ thẻ <...> làm hỏng SSML
    t = re.sub(r"\n+", ". ", t)               # xuống dòng -> dấu chấm
    t = re.sub(r"(\.\s*){2,}", ". ", t)       # gộp dấu chấm lặp
    return t.strip()


def split_into_chunks(text, max_chars=700):
    """Chia văn bản thành các đoạn ngắn, ưu tiên cắt ở cuối câu."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks, current = [], ""
    for s in sentences:
        if len(current) + len(s) + 1 <= max_chars:
            current = f"{current} {s}".strip()
            continue
        if current:
            chunks.append(current)
        # Câu quá dài: cắt tại khoảng trắng gần nhất
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
    async with sem:  # giới hạn số kết nối chạy cùng lúc
        for attempt in range(retries + 1):
            try:
                await edge_tts.Communicate(chunk, voice, rate=rate).save(path)
                return
            except Exception:
                if attempt == retries:
                    raise
                await asyncio.sleep(1)


async def generate_speech_async(
    text,
    output_file="summary_audio.mp3",
    voice=VOICE,
    rate="+0%",          # ví dụ "+10%" để đọc nhanh hơn, "-10%" để chậm hơn
    max_parallel=4,
):
    """Tạo audio bằng cách chia đoạn, chạy song song rồi ghép đúng thứ tự."""
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
        # Ghép theo thứ tự (các file MP3 cùng định dạng nên nối byte được)
        with open(output_file, "wb") as out:
            for p in paths:
                with open(p, "rb") as f:
                    out.write(f.read())

    return output_file