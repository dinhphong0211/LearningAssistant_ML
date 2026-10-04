"""Phát hiện công thức và đơn vị đo bằng luật (heuristic), KHÔNG phải Math OCR.

Mục đích: ghi nhận công thức/số liệu có đơn vị trong tài liệu để
  (1) nhắc mô hình giữ nguyên, và (2) kiểm tra bản tóm tắt có giữ lại hay bịa thêm không.

Giới hạn cần ghi trong báo cáo:
  - Chỉ nhận diện công thức nằm riêng trên một dòng/đoạn dạng văn bản (y = Wx + b),
    hoặc có ký hiệu toán/LaTeX. Công thức là ảnh hoặc PDF dùng font đặc biệt thường bị mất
    hoặc vỡ ký tự ngay từ bước đọc file.
  - Công thức nằm giữa câu văn không được tách riêng.
  - Danh sách đơn vị là danh sách cố định, các đơn vị mơ hồ (m, g, s) bị bỏ qua có chủ ý.
  - Mã nguồn (Python) bị loại bằng luật: dòng có dấu hiệu mã rõ (np.ones, self.x, import, dấu nháy,
    đối số có tên, chỉ mục a[i], **) loại cả khối dòng liền kề. Một dòng gán đơn lẻ như "d = a + b"
    đứng một mình không phân biệt được với công thức nên vẫn được giữ.
"""
import re

_GREEK = "αβγδεζηθικλμνξοπρςστυφχψωΑΒΓΔΘΛΞΠΣΦΨΩ"
_MATH_SYMS = "∑∫√∂∇≈≠≤≥±×÷∈∉⊂⊆∪∩→←⇒∀∃∞·"
_LATEX = re.compile(r"\\(?:frac|sum|int|sqrt|alpha|beta|gamma|theta|lambda|sigma|mathbf|mathbb|log|exp|partial|nabla)")
_SUPER = re.compile(r"[A-Za-z\)\]]\^[\w{(\-]")
_PROSE_TOKEN = re.compile(r"^[^\W\d_]{3,}[.,;:]?$")
_LATEX_SPAN = re.compile(r"\$\$?([^$]{2,120})\$\$?")

# Dấu hiệu mã nguồn mạnh: nếu một dòng có, dòng đó không phải công thức.
_CODE_KEYWORD = re.compile(
    r"^\s*(?:import\b|from\s+\S+\s+import\b|def\b|class\b|for\b|while\b|if\b|elif\b|else\b|with\b|return\b|print\b|assert\b)"
)
_CODE_MARKERS = [
    re.compile(r"\b[A-Za-z_]\w*\.[A-Za-z_]\w*"),      # np.ones, self.tik, d2l.plot, x.grad
    re.compile(r"['\"]"),                               # chuỗi ký tự
    re.compile(r"[,(]\s*[A-Za-z_]\w*\s*=\s*[^=\s]"),   # đối số có tên: figsize=(5, 2.5)
    re.compile(r"[A-Za-z_]\w*\[[^\]]*\]"),             # chỉ mục: a[i], c[i]
    re.compile(r"=\s*[\[{]"),                           # danh sách/từ điển: params = [(0, 1)]
    re.compile(r"\w\(\)"),                              # gọi hàm không đối số: Timer()
    re.compile(r"\*\*"),                                # lũy thừa kiểu Python: sigma**2
]

_UNIT_RE = re.compile(
    r"(?<![\w.])(\d+(?:[.,]\d+)?)\s?(%|ms|GB|MB|KB|TB|GHz|MHz|kHz|Hz|km|cm|mm|kg|°C|px|FLOPs?)(?![A-Za-z])"
)


def looks_like_code(line):
    """True nếu dòng có dấu hiệu mã nguồn rõ ràng (không dùng cho dòng gán trần như 'd = a + b')."""
    s = (line or "").strip()
    if not s:
        return False
    if _CODE_KEYWORD.search(s):
        return True
    return any(m.search(s) for m in _CODE_MARKERS)


def _formula_shape(line):
    """Dòng có dạng công thức (có '=', ký hiệu toán... và ít chữ), chưa xét có phải mã hay không."""
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


def looks_like_formula(line):
    return _formula_shape(line) and not looks_like_code(line)


def _candidate_blocks(text):
    """Chia đoạn thành các khối dòng liền kề có dạng công thức hoặc mã; dòng khác cắt khối."""
    block = []
    for line in text.split("\n"):
        if _formula_shape(line) or looks_like_code(line):
            block.append(line)
        else:
            if block:
                yield block
            block = []
    if block:
        yield block


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
        for block in _candidate_blocks(str(para)):
            # Một khối dòng liền kề mà có dòng là mã thì cả khối là mã (vd n = 10000 đứng cạnh a = np.ones(n)).
            if any(looks_like_code(l) for l in block):
                continue
            for line in block:
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