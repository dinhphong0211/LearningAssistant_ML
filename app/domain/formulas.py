"""Phát hiện công thức và đơn vị đo bằng luật (heuristic), KHÔNG phải Math OCR.

Mục đích: ghi nhận công thức/số liệu có đơn vị trong tài liệu để
  (1) nhắc mô hình giữ nguyên, và (2) kiểm tra bản tóm tắt có giữ lại hay bịa thêm không.

Giới hạn cần ghi trong báo cáo:
  - Chỉ nhận diện công thức nằm riêng trên một dòng/đoạn dạng văn bản (y = Wx + b),
    hoặc có ký hiệu toán/LaTeX. Công thức là ảnh hoặc PDF dùng font đặc biệt thường bị mất
    hoặc vỡ ký tự ngay từ bước đọc file.
  - Công thức nằm giữa câu văn không được tách riêng.
  - Danh sách đơn vị là danh sách cố định, các đơn vị mơ hồ (m, g, s) bị bỏ qua có chủ ý.
"""
import re

_GREEK = "αβγδεζηθικλμνξοπρςστυφχψωΑΒΓΔΘΛΞΠΣΦΨΩ"
_MATH_SYMS = "∑∫√∂∇≈≠≤≥±×÷∈∉⊂⊆∪∩→←⇒∀∃∞·"
_LATEX = re.compile(r"\\(?:frac|sum|int|sqrt|alpha|beta|gamma|theta|lambda|sigma|mathbf|mathbb|log|exp|partial|nabla)")
_SUPER = re.compile(r"[A-Za-z\)\]]\^[\w{(\-]")
_PROSE_TOKEN = re.compile(r"^[^\W\d_]{3,}[.,;:]?$")
_LATEX_SPAN = re.compile(r"\$\$?([^$]{2,120})\$\$?")

_UNIT_RE = re.compile(
    r"(?<![\w.])(\d+(?:[.,]\d+)?)\s?(%|ms|GB|MB|KB|TB|GHz|MHz|kHz|Hz|km|cm|mm|kg|°C|px|FLOPs?)(?![A-Za-z])"
)


def looks_like_formula(line):
    s = (line or "").strip()
    if len(s) < 3 or len(s) > 160:
        return False
    has_latex = bool(_LATEX.search(s))
    has_eq = "=" in s
    has_sym = any(c in _MATH_SYMS or c in _GREEK for c in s)
    has_sup = bool(_SUPER.search(s))
    if not (has_latex or has_eq or has_sym or has_sup):
        return False
    tokens = s.split()
    prose = [t for t in tokens if _PROSE_TOKEN.match(t)]
    return len(prose) <= 2 and len(prose) <= 0.4 * len(tokens)


def extract_formulas(paragraphs, max_items=50):
    """paragraphs: list[str] (hoặc một chuỗi). Trả về danh sách công thức không trùng, giữ thứ tự."""
    if isinstance(paragraphs, str):
        paragraphs = [paragraphs]
    seen, out = set(), []

    def add(f):
        key = re.sub(r"\s+", "", f)
        if key and key not in seen:
            seen.add(key)
            out.append(re.sub(r"\s+", " ", f).strip())

    for para in paragraphs or []:
        for m in _LATEX_SPAN.finditer(para):
            add(m.group(1))
        for line in str(para).split("\n"):
            if looks_like_formula(line):
                add(line)
        if len(out) >= max_items:
            break
    return out[:max_items]


def extract_units(text):
    """Các cặp 'số + đơn vị' (vd '95 %', '16 GB'), không trùng, giữ thứ tự."""
    seen, out = set(), []
    for m in _UNIT_RE.finditer(text or ""):
        item = f"{m.group(1)} {m.group(2)}"
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out
