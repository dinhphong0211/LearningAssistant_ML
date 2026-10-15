"""Nhận diện lĩnh vực/chuyên ngành bằng đếm từ khóa có ranh giới từ, và dựng Domain Profile.

Phương pháp: keyword matching (không học máy). Điểm của một lĩnh vực = tổng số lần các từ khóa
của nó xuất hiện; độ tin cậy = phần trăm điểm của lĩnh vực thắng trên tổng điểm mọi lĩnh vực.

Giới hạn cần ghi trong báo cáo:
  - Độ tin cậy là "thị phần từ khóa", KHÔNG phải xác suất đã hiệu chỉnh.
  - Chỉ biết các lĩnh vực có trong DOMAIN_PROFILES; tài liệu ngoài danh sách được gán sai
    hoặc "General/Unknown".
  - Bộ phân loại học máy (TF-IDF + Logistic Regression) trong ml_classifier.py thắng bộ đếm từ khóa
    này trên tập D2L (xem results/reliability_*.md); từ khóa chỉ còn là baseline và là nguồn thuật ngữ.
  - Các từ khóa mơ hồ (feature, training, f1, git) đã bị loại vì xuất hiện ở nhiều lĩnh vực.
"""
import re
from collections import Counter

# Mỗi lĩnh vực: danh sách từ khóa (viết thường, có thể là cụm tiếng Việt hoặc tiếng Anh)
DOMAIN_PROFILES = {
    "Machine Learning": [
        "học máy", "machine learning", "học có giám sát", "supervised learning", "unsupervised learning",
        "học không giám sát", "hồi quy", "regression", "phân loại", "classification", "overfitting",
        "underfitting", "cross-validation", "đặc trưng", "svm", "decision tree", "cây quyết định",
        "random forest", "k-means", "gradient descent", "hàm mất mát", "loss function", "epoch",
        "huấn luyện", "dataset", "tập dữ liệu", "accuracy", "precision", "recall",
    ],
    "Deep Learning": [
        "học sâu", "deep learning", "neural network", "mạng nơ-ron", "mạng neural", "cnn", "rnn", "lstm",
        "gru", "backpropagation", "lan truyền ngược", "activation", "hàm kích hoạt", "relu", "softmax",
        "dropout", "convolution", "tích chập", "transformer", "attention", "batch normalization", "gpu",
    ],
    "Natural Language Processing": [
        "xử lý ngôn ngữ tự nhiên", "natural language processing", "nlp", "tokenization", "tokenizer",
        "embedding", "word2vec", "bert", "gpt", "named entity", "ner", "pos tagging", "sentiment",
        "phân tích cảm xúc", "tóm tắt văn bản", "text summarization", "mô hình ngôn ngữ", "language model",
        "bleu", "rouge", "seq2seq", "corpus", "ngữ liệu",
    ],
    "Software Engineering & Web": [
        "lập trình", "phần mềm", "controller", "route", "framework", "laravel", "php", "api", "frontend",
        "backend", "artisan", "visual studio code", "scrum", "agile", "docker", "html", "css", "javascript",
        "python", "kiểm thử phần mềm", "unit test", "uml", "use case", "mvc", "kiến trúc phần mềm",
        "devops", "ci/cd", "yêu cầu phần mềm", "lập trình hướng đối tượng", "oop",
    ],
    "Mathematics": [
        "đạo hàm", "tích phân", "ma trận", "vector", "phương trình", "định lý", "xác suất", "thống kê",
        "giải tích", "đại số", "đồ thị", "derivative", "integral", "matrix", "probability", "theorem",
    ],
    "Computer Networks": [
        "mạng máy tính", "computer network", "giao thức", "protocol", "tcp", "udp", "tcp/ip", "địa chỉ ip",
        "ip address", "định tuyến", "routing", "router", "bộ định tuyến", "switch", "chuyển mạch", "gói tin",
        "packet", "băng thông", "bandwidth", "độ trễ", "latency", "dns", "http", "https", "ethernet", "wifi",
        "mô hình osi", "osi", "subnet", "mạng con", "tên miền",
    ],
    "Databases": [
        "cơ sở dữ liệu", "database", "csdl", "sql", "truy vấn", "query", "khóa chính", "primary key",
        "khóa ngoại", "foreign key", "phụ thuộc hàm", "functional dependency", "giao dịch", "transaction",
        "acid", "chỉ mục", "mô hình quan hệ", "relational", "nosql", "inner join", "đại số quan hệ",
        "mongodb", "mysql", "postgresql", "lược đồ", "schema", "hệ quản trị cơ sở dữ liệu", "dbms",
    ],
    "Operating Systems": [
        "hệ điều hành", "operating system", "tiến trình", "thread", "đa luồng", "multithreading", "lập lịch",
        "scheduling", "deadlock", "bế tắc", "semaphore", "mutex", "bộ nhớ ảo", "virtual memory", "phân trang",
        "paging", "phân đoạn", "hệ thống tệp", "file system", "kernel", "nhân hệ điều hành", "ngắt",
        "interrupt", "context switch", "chuyển ngữ cảnh", "round robin", "linux", "unix", "system call",
        "lời gọi hệ thống",
    ],
    "Algorithms & Data Structures": [
        "thuật toán", "algorithm", "cấu trúc dữ liệu", "data structure", "độ phức tạp", "complexity", "big o",
        "sắp xếp", "sorting", "tìm kiếm nhị phân", "binary search", "danh sách liên kết", "linked list",
        "ngăn xếp", "stack", "hàng đợi", "queue", "cây nhị phân", "binary tree", "bảng băm", "hash table",
        "đệ quy", "recursion", "quy hoạch động", "dynamic programming", "tham lam", "greedy", "bfs", "dfs",
        "dijkstra", "heap", "quicksort", "merge sort", "quick sort",
    ],
    "Information Security": [
        "an toàn thông tin", "bảo mật", "security", "mã hóa", "encryption", "giải mã", "decryption",
        "khóa công khai", "public key", "rsa", "aes", "hàm băm", "hash function", "chữ ký số",
        "digital signature", "tường lửa", "firewall", "xác thực", "authentication", "phân quyền",
        "authorization", "lỗ hổng", "vulnerability", "tấn công", "attack", "malware", "mã độc", "phishing",
        "xss", "sql injection", "ddos", "chứng chỉ số", "ssl", "tls", "vpn",
    ],
}

PARENT_DOMAIN = {
    "Machine Learning": "Computer Science / AI",
    "Deep Learning": "Computer Science / AI",
    "Natural Language Processing": "Computer Science / AI",
    "Software Engineering & Web": "Computer Science / Software",
    "Mathematics": "Mathematics",
    "Computer Networks": "Computer Science / Networking",
    "Databases": "Computer Science / Data",
    "Operating Systems": "Computer Science / Systems",
    "Algorithms & Data Structures": "Computer Science / Theory",
    "Information Security": "Computer Science / Security",
}

_VI_CHARS = re.compile(
    r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]", re.IGNORECASE
)


def _keyword_pattern(keyword):
    # Ranh giới từ kiểu "không dính chữ/số hai bên", dùng được cho cụm tiếng Việt nhiều âm tiết
    return re.compile(rf"(?<!\w){re.escape(keyword.lower())}(?!\w)")


_COMPILED = {}


def _compiled(domain_profiles):
    key = id(domain_profiles)
    if key not in _COMPILED:
        _COMPILED[key] = {
            d: [_keyword_pattern(k) for k in kws] for d, kws in domain_profiles.items()
        }
    return _COMPILED[key]


def score_domains(text, domain_profiles=DOMAIN_PROFILES):
    """Điểm từng lĩnh vực (số lần xuất hiện từ khóa)."""
    low = (text or "").lower()
    patterns = _compiled(domain_profiles)
    return {d: sum(len(p.findall(low)) for p in pats) for d, pats in patterns.items()}


def detect_domain(text, domain_profiles=DOMAIN_PROFILES):
    """Trả về (tên lĩnh vực, độ tin cậy %). Giữ nguyên chữ ký cũ để pipeline không đổi."""
    if not text or not text.strip():
        return "Unknown", 0.0
    scores = score_domains(text, domain_profiles)
    total = sum(scores.values())
    if total == 0:
        return "General/Unknown", 0.0
    best = max(scores, key=scores.get)
    return best, round(scores[best] / total * 100, 2)


def detect_language(text):
    """Đoán ngôn ngữ chính: tỉ lệ chữ có dấu tiếng Việt trên tổng chữ cái."""
    letters = [c for c in (text or "") if c.isalpha()]
    if len(letters) < 20:
        return "Unknown"
    ratio = len(_VI_CHARS.findall(text)) / len(letters)
    if ratio > 0.06:
        return "Vietnamese"
    if ratio < 0.01:
        return "English"
    return "Mixed"


def _top_concepts(text, terms, k=10):
    low = (text or "").lower()
    counts = []
    for t in terms or []:
        n = len(_keyword_pattern(t).findall(low))
        if n:
            counts.append((n, t))
    counts.sort(key=lambda x: (-x[0], x[1].lower()))
    return [t for _, t in counts[:k]]


def build_domain_profile(text, terms=None, abbreviations=None, formulas=None, units=None):
    """Domain Profile theo mô tả đồ án. `important_concepts` = thuật ngữ xuất hiện nhiều nhất (heuristic)."""
    sub, conf = detect_domain(text)
    scores = score_domains(text)
    ranked = sorted(((s, d) for d, s in scores.items() if s > 0), reverse=True)
    return {
        "domain": PARENT_DOMAIN.get(sub, sub),
        "subdomain": sub,
        "confidence": conf,
        "alternatives": [d for _, d in ranked[1:3]],
        "language": detect_language(text),
        "technical_terms": list(terms or []),
        "abbreviations": dict(abbreviations or {}),
        "important_concepts": _top_concepts(text, terms),
        "formulas": list(formulas or []),
        "units": list(units or []),
    }
