"""Sinh câu hỏi trắc nghiệm từ nội dung bài học.

Hai đường:
  1. generate_ai: nhờ Gemini ra đề dạng JSON, rồi KIỂM CHỨNG từng câu với văn bản gốc
     (câu nào có "bằng chứng" không nằm trong tài liệu, hoặc đáp án không có trong tài liệu, bị loại).
  2. generate_local: điền khuyết bằng luật, không gọi API: che một thuật ngữ trong câu của tài liệu,
     đáp án nhiễu lấy từ các thuật ngữ khác của chính tài liệu; thêm câu hỏi "viết tắt của gì".

generate_quiz ghép hai đường: ưu tiên Gemini, thiếu thì bù bằng điền khuyết (cũng là phương án
khi hết hạn mức). Giới hạn: kiểm chứng dựa trên trùng từ vựng, không hiểu ngữ nghĩa; câu điền khuyết
chỉ tốt bằng chất lượng danh sách thuật ngữ đầu vào.
"""
import json
import random
import re

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_TOKEN = re.compile(r"\w+", re.UNICODE)

# Từ không nên làm đáp án điền khuyết
TERM_STOP = {
    "trong", "các", "những", "một", "để", "của", "và", "với", "cho", "khi", "nếu", "này", "đó",
    "section", "fig", "figure", "table", "chapter", "bước", "phần", "kết quả", "ví dụ", "lưu ý",
    "code", "design", "review", "event", "role", "demo",
}

QUIZ_PROMPT = """Bạn là giáo viên ra đề trắc nghiệm. Dựa CHỈ vào văn bản dưới đây, hãy tạo {n} câu hỏi trắc nghiệm 4 lựa chọn bằng tiếng Việt.
Yêu cầu:
- Mỗi câu kiểm tra một ý quan trọng, có đúng 1 đáp án đúng và 3 đáp án nhiễu hợp lý nhưng SAI theo văn bản.
- Không hỏi điều văn bản không nói tới. Giữ nguyên thuật ngữ, viết tắt, số liệu.
- Khóa evidence: chép NGUYÊN VĂN một câu hoặc cụm trong văn bản chứng minh đáp án đúng.
- Chỉ trả về MỘT mảng JSON, không markdown, không lời dẫn. Mỗi phần tử có đúng các khóa: "q" (câu hỏi), "options" (mảng 4 chuỗi), "answer" (số từ 0 đến 3), "explain" (một câu giải thích), "evidence".

Văn bản:
{text}"""


def tokens(text):
    return _TOKEN.findall((text or "").lower())


def split_sentences(text, min_words=7, max_words=45):
    out, seen = [], set()
    for s in _SENT_SPLIT.split(text or ""):
        s = " ".join(s.split())
        n = len(_TOKEN.findall(s))
        if min_words <= n <= max_words and s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    return out


def candidate_terms(terms):
    """Lọc danh sách thuật ngữ để làm đáp án: bỏ từ quá ngắn/dài, từ dừng, đường dẫn/lệnh code."""
    seen, out = set(), []
    for t in terms or []:
        t = " ".join(str(t).split())
        key = t.lower()
        if not (3 <= len(t) <= 40) or key in seen or key in TERM_STOP or t.isdigit() or len(t.split()) > 4:
            continue
        if re.search(r"[:/\\.]", t):
            continue
        seen.add(key)
        out.append(t)
    return out


def _term_re(term):
    return re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", re.IGNORECASE)


# ---------------------------------------------------------------- điền khuyết (không cần API)
def generate_local(text, terms, abbreviations=None, n=8, seed=0):
    rng = random.Random(seed)
    pool = candidate_terms(terms)
    sents = split_sentences(text)
    questions, used = [], set()

    # (a) Câu hỏi viết tắt
    abbr = {a: f for a, f in (abbreviations or {}).items() if a and f}
    expansions = list(abbr.values())
    max_abbr = max(0, n // 4)
    for a, full in rng.sample(list(abbr.items()), len(abbr)):
        if len(questions) >= max_abbr:
            break
        others = [e for e in expansions if e.lower() != full.lower()]
        if len(others) < 3:
            continue
        opts = rng.sample(others, 3) + [full]
        rng.shuffle(opts)
        questions.append({
            "type": "abbreviation",
            "q": f"Theo tài liệu, {a} là viết tắt của cụm nào?",
            "options": opts, "answer": opts.index(full),
            "explain": f"Tài liệu định nghĩa: {full} ({a}).",
            "evidence": f"{full} ({a})", "source": "offline",
        })

    # (b) Điền khuyết thuật ngữ
    order = list(range(len(sents)))
    rng.shuffle(order)
    for i in order:
        if len(questions) >= n:
            break
        s = sents[i]
        hits = [t for t in pool if t.lower() not in used and _term_re(t).search(s)]
        if not hits:
            continue
        term = max(hits, key=len)
        rx = _term_re(term)
        others = [t for t in pool if t.lower() != term.lower() and not _term_re(t).search(s)]
        others.sort(key=lambda t: (abs(len(t.split()) - len(term.split())), abs(len(t) - len(term))))
        near = others[:8]
        if len(near) < 3:
            continue
        opts = rng.sample(near, 3) + [term]
        rng.shuffle(opts)
        used.add(term.lower())
        questions.append({
            "type": "cloze",
            "q": "Điền vào chỗ trống: " + rx.sub("_____", s),
            "options": opts, "answer": opts.index(term),
            "explain": f"Câu gốc trong tài liệu: {s}",
            "evidence": s, "source": "offline",
        })
    return questions[:n]


# ---------------------------------------------------------------- Gemini + kiểm chứng
def _sample_text(text, limit=12000, parts=4):
    """Tài liệu dài: lấy `parts` đoạn cách đều thay vì chỉ phần đầu."""
    if len(text) <= limit:
        return text
    size = limit // parts
    step = (len(text) - size) / max(1, parts - 1)
    return "\n\n".join(text[int(i * step): int(i * step) + size] for i in range(parts))


def parse_quiz_json(raw):
    s = (raw or "").strip()
    m = re.search(r"\[.*\]", s, re.S)
    if m:
        s = m.group(0)
    data = json.loads(s)
    if not isinstance(data, list):
        raise ValueError("Gemini không trả về mảng câu hỏi")
    return data


def _coverage(tok, src_set):
    return (sum(1 for t in tok if t in src_set) / len(tok)) if tok else 0.0


def validate_ai_questions(items, source_text, rng=None, min_evidence=0.8, min_answer=0.5):
    """Trả về (câu hợp lệ, danh sách lý do loại). Đáp án được xáo lại vị trí."""
    rng = rng or random.Random(0)
    src = set(tokens(source_text))
    kept, dropped, seen_q = [], [], set()
    for it in items:
        try:
            q = str(it["q"]).strip()
            opts = [str(o).strip() for o in it["options"]]
            ans = int(it["answer"])
            ev = str(it.get("evidence", "")).strip()
            explain = str(it.get("explain", "")).strip()
        except Exception:
            dropped.append("sai định dạng")
            continue
        if not q or len(opts) != 4 or not 0 <= ans < 4 or len({o.lower() for o in opts}) != 4 or "" in opts:
            dropped.append("sai định dạng")
            continue
        if q.lower() in seen_q:
            dropped.append("trùng câu hỏi")
            continue
        ev_tok = tokens(ev)
        if len(ev_tok) < 3 or _coverage(ev_tok, src) < min_evidence:
            dropped.append("bằng chứng không có trong tài liệu")
            continue
        if _coverage(tokens(opts[ans]), src) < min_answer:
            dropped.append("đáp án không có trong tài liệu")
            continue
        correct = opts[ans]
        rng.shuffle(opts)
        seen_q.add(q.lower())
        kept.append({
            "type": "mcq", "q": q, "options": opts, "answer": opts.index(correct),
            "explain": explain or f"Căn cứ: {ev}", "evidence": ev, "source": "gemini",
        })
    return kept, dropped


def generate_ai(summarizer, text, n):
    raw = summarizer._generate(QUIZ_PROMPT.format(n=n, text=_sample_text(text)))
    return parse_quiz_json(raw)


def generate_quiz(summarizer, text, terms=None, abbreviations=None, n=8, use_ai=True, seed=0):
    """Trả về (danh sách câu hỏi, báo cáo). Không bao giờ ném lỗi API ra ngoài."""
    rng = random.Random(seed)
    report = {"requested": n, "gemini": 0, "gemini_dropped": 0, "offline": 0,
              "error": None, "dropped_reasons": []}
    questions = []
    if use_ai and summarizer is not None and (text or "").strip():
        try:
            items = generate_ai(summarizer, text, n + 2)
            kept, dropped = validate_ai_questions(items, text, rng)
            questions = kept[:n]
            report["gemini"] = len(questions)
            report["gemini_dropped"] = len(dropped)
            report["dropped_reasons"] = sorted(set(dropped))
        except Exception as e:
            report["error"] = f"{type(e).__name__}: {e}"
    if len(questions) < n:
        have = {q["q"].lower() for q in questions}
        for q in generate_local(text, terms, abbreviations, n - len(questions), seed):
            if q["q"].lower() not in have:
                questions.append(q)
                report["offline"] += 1
    return questions[:n], report
