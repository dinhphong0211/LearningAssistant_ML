import re


def chunk_text(text, max_chars=6000, overlap=300):
    """Chia văn bản thành các đoạn <= max_chars, ưu tiên cắt ở cuối câu,
    mỗi đoạn mang theo `overlap` ký tự cuối của đoạn trước."""
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []

    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks, current = [], ""
    for s in sentences:
        if current and len(current) + len(s) + 1 > max_chars:
            chunks.append(current)
            tail = current[-overlap:] if overlap else ""
            if " " in tail:                      # không bắt đầu giữa chừng một từ
                tail = tail.split(" ", 1)[1]
            current = tail
        current = f"{current} {s}".strip()

        # Câu quá dài (không có dấu chấm): cắt cứng
        while len(current) > max_chars:
            chunks.append(current[:max_chars])
            current = current[max_chars - overlap:] if overlap else current[max_chars:]

    if current.strip():
        chunks.append(current)
    return chunks