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


def chunk_paragraphs(paragraphs, max_chars=6000):
    """Gom các đoạn văn thành các khối <= max_chars, giữ ranh giới đoạn, KHÔNG chồng lấn.

    Dùng cho chế độ đọc toàn bộ: ghép lại các khối theo thứ tự phải ra đúng văn bản gốc,
    không lặp và không mất chữ (khác chunk_text vốn cố ý lặp `overlap` ký tự).
    Đoạn dài hơn max_chars được cắt ở cuối câu."""
    chunks, current, size = [], [], 0
    for p in paragraphs:
        p = (p or "").strip()
        if not p:
            continue
        pieces = [p] if len(p) <= max_chars else chunk_text(p, max_chars=max_chars, overlap=0)
        for piece in pieces:
            add = len(piece) + (2 if current else 0)
            if current and size + add > max_chars:
                chunks.append("\n\n".join(current))
                current, size, add = [], 0, len(piece)
            current.append(piece)
            size += add
    if current:
        chunks.append("\n\n".join(current))
    return chunks
