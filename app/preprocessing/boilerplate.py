"""Loại 'nhiễu trình bày' (số trang, header/footer lặp lại) bằng luật, không cần AI.

Dùng cho chế độ "Đọc toàn bộ": giữ nguyên nội dung, chỉ bỏ những thứ vô nghĩa khi nghe.

Nguyên tắc: thà bỏ sót còn hơn xóa nhầm nội dung. Vì vậy:
- Header/footer chỉ bị coi là nhiễu khi nằm sát mép trang VÀ lặp lại trên nhiều trang.
- Tên tác giả, mục lục... cần hiểu ngữ nghĩa nên không xử lý ở đây (để Gemini làm).
"""
import math
import re

# Số trang đứng riêng một dòng: "12", "- 12 -", "[12]"
_BARE_NUMBER = re.compile(r"^[\s\-–—•·\[\(<]*\d{1,3}[\s\-–—•·\]\)>]*$")
# Có chữ đánh dấu: "Trang 12", "Page 3 of 10", "tr. 5", "p.7"
_MARKED = re.compile(
    r"^[\s\-–—•·\[\(<]*(?:trang|page|pg|tr|p)\.?\s*\d{1,4}"
    r"(?:\s*(?:/|of|trên)\s*\d{1,4})?[\s\-–—•·\]\)>]*$",
    re.IGNORECASE,
)
# Dạng phân số: "3/10", "3 of 10"
_FRACTION = re.compile(r"^\s*\d{1,4}\s*(?:/|of|trên)\s*\d{1,4}\s*$", re.IGNORECASE)


def is_page_number(line, strict=False):
    """strict=True: chỉ nhận dạng có chữ 'Trang/Page' hoặc 'x/y', không nhận số trần
    (dùng khi dòng nằm giữa đoạn văn, nơi một số đứng riêng có thể là nội dung thật)."""
    s = (line or "").strip()
    if not s or len(s) > 24:
        return False
    if _MARKED.match(s) or _FRACTION.match(s):
        return True
    return (not strict) and bool(_BARE_NUMBER.match(s))


def _signature(text):
    """Chuẩn hóa để so sánh header/footer giữa các trang: 'Trang 3' và 'Trang 4' cùng chữ ký."""
    t = re.sub(r"\s+", " ", (text or "").lower()).strip()
    return re.sub(r"\d+", "#", t)


MAX_FURNITURE_CHARS = 120  # header/footer thật hiếm khi dài hơn một dòng ngắn


def _repeated(counts, n_pages, min_pages, min_ratio):
    if n_pages < min_pages:
        return set()
    need = max(min_pages, math.ceil(min_ratio * n_pages))
    return {sig for sig, c in counts.items() if sig and len(sig) <= MAX_FURNITURE_CHARS and c >= need}


def filter_pdf_furniture(pages, margin=0.09, min_pages=3, min_ratio=0.4):
    """Bỏ số trang và header/footer lặp lại khỏi các block của PDF.

    pages: list các (chiều_cao_trang, blocks); mỗi block theo định dạng của
           PyMuPDF get_text("blocks"): (x0, y0, x1, y1, text, block_no, block_type).
    Trả về danh sách block còn lại (phẳng, giữ nguyên thứ tự).

    Một block bị bỏ khi: nằm hoàn toàn trong dải mép trên/dưới (margin * chiều cao) và
    (là số trang, hoặc có cùng chữ ký trên >= min_ratio số trang, tối thiểu min_pages trang).
    Block ảnh luôn bị bỏ vì chúng không có văn bản thật.
    """
    def is_text(b):
        return len(b) <= 6 or b[6] == 0

    def in_margin(b, h):
        return h > 0 and (b[3] <= h * margin or b[1] >= h * (1 - margin))

    counts = {}
    for h, blocks in pages:
        sigs = {_signature(b[4]) for b in blocks if is_text(b) and in_margin(b, h) and str(b[4]).strip()}
        for s in sigs:
            counts[s] = counts.get(s, 0) + 1
    repeated = _repeated(counts, len(pages), min_pages, min_ratio)

    kept = []
    for h, blocks in pages:
        for b in blocks:
            if not is_text(b):
                continue
            text = str(b[4]).strip()
            if text and in_margin(b, h) and (is_page_number(text) or _signature(text) in repeated):
                continue
            kept.append(b)
    return kept


def strip_repeated_page_lines(pages, edge_lines=2, min_pages=3, min_ratio=0.4):
    """Tương tự filter_pdf_furniture nhưng cho văn bản thuần theo từng trang (kết quả OCR).

    pages: list chuỗi, mỗi chuỗi là văn bản của một trang. Chỉ xét `edge_lines` dòng đầu
    và cuối của mỗi trang. Trả về list chuỗi đã loại dòng nhiễu."""
    split = [p.splitlines() for p in pages]

    def edge_indices(lines):
        idx = [i for i, ln in enumerate(lines) if ln.strip()]
        return set(idx[:edge_lines] + idx[-edge_lines:])

    edges = [edge_indices(lines) for lines in split]
    counts = {}
    for lines, edge in zip(split, edges):
        for sig in {_signature(lines[i]) for i in edge}:
            counts[sig] = counts.get(sig, 0) + 1
    repeated = _repeated(counts, len(pages), min_pages, min_ratio)

    out = []
    for lines, edge in zip(split, edges):
        keep = [
            ln for i, ln in enumerate(lines)
            if not (i in edge and (is_page_number(ln) or _signature(ln) in repeated))
        ]
        out.append("\n".join(keep).strip())
    return out


def drop_page_number_paragraphs(paragraphs):
    """Bỏ đoạn chỉ gồm số trang, và bỏ dòng 'Trang x' / 'x/y' nằm lẫn trong đoạn nhiều dòng."""
    out = []
    for p in paragraphs:
        lines = p.splitlines()
        if len(lines) <= 1:
            if not is_page_number(p):
                out.append(p)
            continue
        kept = "\n".join(ln for ln in lines if not is_page_number(ln, strict=True)).strip()
        if kept:
            out.append(kept)
    return out
