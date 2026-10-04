"""Phát hiện từ viết tắt và dạng đầy đủ của chúng trong tài liệu.

Hai mẫu được nhận diện:
  - "Long Short-Term Memory (LSTM)"   -> LSTM = Long Short-Term Memory
  - "LSTM (Long Short-Term Memory)"   -> LSTM = Long Short-Term Memory

Thuật toán ghép chữ cái là bản cài đặt đơn giản của Schwartz & Hearst (2003),
"A Simple Algorithm for Identifying Abbreviation Definitions in Biomedical Text":
duyệt các chữ cái của từ viết tắt từ phải sang trái và tìm chúng trong cụm từ đứng trước
dấu ngoặc; chữ cái đầu của từ viết tắt phải trùng với chữ đầu của một từ.

Nguyên tắc (theo yêu cầu đồ án): CHỈ ghi nhận cách mở rộng mà chính tài liệu định nghĩa.
Hệ thống không tự suy đoán "AI" là gì khi tài liệu không nói.

Giới hạn: định nghĩa tiếng Việt như "Trí tuệ nhân tạo (AI)" không ghép được bằng chữ cái đầu
nên không được nhận diện; những từ viết tắt đó chỉ xuất hiện ở danh sách "chưa có định nghĩa".
"""
import re

_PAREN = re.compile(r"\(([^()\n]{2,40})\)")
_ABBR_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-\.]{1,9}$")
_ACRONYM_USE = re.compile(r"(?<![\w-])([A-Z][A-Z0-9]{1,5})(?![\w-])")


def _looks_like_abbr(s):
    s = s.strip()
    if not _ABBR_TOKEN.match(s) or len(s.split()) > 1:
        return False
    upper = sum(1 for c in s if c.isupper())
    return upper >= 2


def _best_long_form(short, long_text):
    """Schwartz-Hearst: tìm cụm từ trong long_text mà `short` là chữ viết tắt. None nếu không ghép được."""
    s_idx = len(short) - 1
    l_idx = len(long_text) - 1
    while s_idx >= 0:
        c = short[s_idx].lower()
        if not c.isalnum():
            s_idx -= 1
            continue
        while l_idx >= 0 and (
            long_text[l_idx].lower() != c
            or (s_idx == 0 and l_idx > 0 and long_text[l_idx - 1].isalnum())
        ):
            l_idx -= 1
        if l_idx < 0:
            return None
        l_idx -= 1
        s_idx -= 1
    start = long_text.rfind(" ", 0, l_idx + 1) + 1
    return long_text[start:].strip()


def _clean_long(s):
    return re.sub(r"\s+", " ", s).strip(" ,;:-")


def extract_abbreviations(text):
    """Trả về dict {viết tắt: dạng đầy đủ}. Định nghĩa xuất hiện đầu tiên được giữ."""
    found = {}
    if not text:
        return found
    for m in _PAREN.finditer(text):
        inner = m.group(1).strip()
        before = text[: m.start()].rstrip()

        # Mẫu 1: "Long Form (ABBR)"
        if _looks_like_abbr(inner):
            words = before.split()
            n = len(inner)
            candidate = " ".join(words[-min(n + 5, n * 2):])
            long_form = _best_long_form(inner, candidate)
            if long_form:
                n_words = len(long_form.split())
                if (len(long_form) > len(inner) and n_words <= min(n + 5, n * 2)
                        and inner.lower() not in long_form.lower().split()):
                    found.setdefault(inner, _clean_long(long_form))
                    continue

        # Mẫu 2: "ABBR (Long Form)"
        prev = before.split()[-1] if before.split() else ""
        if _looks_like_abbr(prev) and len(inner.split()) >= 2:
            long_form = _best_long_form(prev, inner)
            if long_form and len(long_form.split()) >= 2:
                found.setdefault(prev, _clean_long(long_form))
    return found


def find_undefined_abbreviations(text, defined, min_count=2):
    """Từ viết tắt IN HOA xuất hiện từ `min_count` lần nhưng tài liệu không định nghĩa."""
    counts = {}
    for m in _ACRONYM_USE.finditer(text or ""):
        counts[m.group(1)] = counts.get(m.group(1), 0) + 1
    return sorted(a for a, c in counts.items() if c >= min_count and a not in defined)


def abbreviation_conflicts(summary, source_abbreviations):
    """Tìm chỗ bản tóm tắt định nghĩa một từ viết tắt KHÁC với tài liệu gốc."""
    conflicts = []
    in_summary = extract_abbreviations(summary)
    for abbr, long_form in in_summary.items():
        original = source_abbreviations.get(abbr)
        if original and _clean_long(original).lower() != _clean_long(long_form).lower():
            conflicts.append({"abbreviation": abbr, "source": original, "summary": long_form})
    return conflicts
