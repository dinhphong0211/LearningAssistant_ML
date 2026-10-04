"""Bổ sung thuật ngữ bằng tra từ điển lĩnh vực.

Vấn đề: extract_terminology() chỉ bắt từ viết tắt, CamelCase, cụm viết hoa và đoạn mã, nên bỏ sót
phần lớn thuật ngữ viết thường trong giáo trình ("hàm mất mát", "gradient descent", "hồi quy").
Cách xử lý: lấy các từ khóa của (những) lĩnh vực nổi bật nhất trong DOMAIN_PROFILES xuất hiện trong văn bản.

Giới hạn cần ghi trong báo cáo:
  - Chỉ nhận ra thuật ngữ có trong từ điển (khoảng 130 mục cho ML, DL, NLP, Software, Math); thuật ngữ
    ngoài từ điển vẫn bị bỏ sót. Đây là tra cứu từ điển, KHÔNG phải mô hình học máy.
  - Một số mục từ điển là từ thông dụng (training, feature) nên có thể đưa vào cả những từ ít mang tính thuật ngữ.
"""
import re
from collections import Counter

from domain.detector import DOMAIN_PROFILES, score_domains


_SENTENCE_START = re.compile(r"(?:^|[.!?:]\s+|\n\s*)$")


def _surface_form(text, matches, keyword):
    """Chọn dạng hiển thị của một mục từ điển.
    - Ưu tiên các lần xuất hiện KHÔNG đứng đầu câu (để "Hàm mất mát" đầu câu không thành dạng chuẩn).
    - Nếu mọi lần đều đứng đầu câu: dùng dạng trong từ điển (thường là chữ thường).
    - Từ IN HOA toàn bộ (CNN, GPU) luôn giữ nguyên."""
    inner = [m.group(0) for m in matches if not _SENTENCE_START.search(text[: m.start()])]
    pool = Counter(inner) if inner else None
    if pool is None:
        allcaps = Counter(m.group(0) for m in matches if m.group(0).isupper())
        return allcaps.most_common(1)[0][0] if allcaps else keyword
    return min(pool, key=lambda s: (s != s.lower() and not s.isupper(), -pool[s]))


def lexicon_terms(text, domain_profiles=DOMAIN_PROFILES, rel_threshold=0.25):
    """Từ khóa từ điển có mặt trong text, thuộc các lĩnh vực có điểm >= rel_threshold * điểm cao nhất."""
    if not text or not text.strip():
        return []
    scores = score_domains(text, domain_profiles)
    top = max(scores.values(), default=0)
    if top == 0:
        return []
    found = {}
    for domain, score in scores.items():
        if score < rel_threshold * top:
            continue
        for kw in domain_profiles[domain]:
            if kw in found:
                continue
            pattern = re.compile(rf"(?<!\w){re.escape(kw)}(?!\w)", re.IGNORECASE)
            matches = list(pattern.finditer(text))
            if matches:
                found[kw] = _surface_form(text, matches, kw)
    return sorted(found.values(), key=str.lower)


def add_lexicon_terms(terms, text):
    """Gộp danh sách thuật ngữ đã lọc với thuật ngữ từ điển, bỏ trùng không phân biệt hoa/thường."""
    seen = {t.lower() for t in terms}
    merged = list(terms)
    for t in lexicon_terms(text):
        if t.lower() not in seen:
            seen.add(t.lower())
            merged.append(t)
    return sorted(merged, key=str.lower)
