"""Lọc và gộp danh sách thuật ngữ do extract_terminology() trả về.

Đây là bước hậu xử lý theo luật (heuristic), KHÔNG phải mô hình học máy.
Các luật:
  1. Gộp biến thể chỉ khác hoa/thường (BACKLOG / Backlog / backlog) thành một mục.
  2. Từ in hoa toàn bộ dài hơn 5 ký tự thường là tiêu đề PDF viết hoa -> đưa về dạng Title Case.
     Từ in hoa ngắn (AI, API, PBI, ROI) được coi là từ viết tắt -> giữ nguyên.
  3. Bỏ cụm quá dài (> max_words từ), thường là do ghép nhầm nhiều thuật ngữ.
  4. Bỏ từ đơn nằm trong stoplist.
  5. Với từ đơn không phải viết tắt: chỉ giữ nếu trong tài liệu nó chủ yếu viết hoa
     (tỉ lệ >= 70%) và xuất hiện >= min_count lần. Từ thông thường như "code", "design"
     thường viết thường nên bị loại.
Giới hạn: luật đơn giản có thể loại nhầm thuật ngữ đơn hợp lệ viết thường (vd "backlog").
"""
import re

DEFAULT_STOPLIST = {
    "code", "design", "marketing", "review", "role", "event", "khung", "master",
    "owner", "demo", "minh",
}


def _is_acronym(term):
    return term.isupper() and 2 <= len(term) <= 5 and " " not in term


def _count_variants(text, term):
    """Đếm số lần xuất hiện của term (không phân biệt hoa/thường) và số lần viết hoa chữ đầu."""
    pattern = re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", re.IGNORECASE)
    total = capitalized = 0
    for m in pattern.finditer(text):
        total += 1
        if m.group(0)[:1].isupper():
            capitalized += 1
    return total, capitalized


def clean_terms(terms, text="", min_count=2, max_words=4, stoplist=None):
    stoplist = {s.lower() for s in (stoplist if stoplist is not None else DEFAULT_STOPLIST)}
    groups = {}
    for raw in terms or []:
        t = " ".join(str(raw).split())
        if not t:
            continue
        groups.setdefault(t.lower(), []).append(t)

    cleaned = []
    for key, variants in groups.items():
        words = key.split()
        if len(words) > max_words:
            continue
        if key in stoplist:
            continue

        # Chọn dạng hiển thị
        acronym = next((v for v in variants if _is_acronym(v)), None)
        if acronym:
            display = acronym
        else:
            mixed = [v for v in variants if not v.isupper()]
            display = mixed[0] if mixed else variants[0].title()

        # Từ đơn không phải viết tắt: cần bằng chứng từ văn bản
        if len(words) == 1 and not acronym and text:
            total, capitalized = _count_variants(text, key)
            if total < min_count or capitalized / total < 0.7:
                continue

        cleaned.append(display)

    return sorted(cleaned, key=str.lower)
