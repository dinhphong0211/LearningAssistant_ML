"""Bộ phân loại lĩnh vực bằng học máy có giám sát: TF-IDF + Logistic Regression (hoặc Naive Bayes).

Đây là thành phần HỌC MÁY THẬT do đồ án tự huấn luyện (khác TextRank không giám sát và Gemini chỉ inference).
So sánh với bộ đếm từ khóa trong detector.py trên cùng dữ liệu.

Bố cục dữ liệu:  data/domain/<nhãn>/<tên tài liệu>.txt
  - Mỗi file = MỘT tài liệu. Thư mục = nhãn lĩnh vực (xem SLUGS).
  - Mỗi tài liệu được cắt thành các đoạn ~N từ làm mẫu huấn luyện/đánh giá.
  - Chia tập theo TÀI LIỆU (GroupKFold), không theo đoạn, để đoạn của cùng một tài liệu
    không nằm ở cả train và test (rò rỉ dữ liệu).

Giới hạn cần ghi trong báo cáo:
  - Nhãn lấy theo thư mục do người làm đồ án gán (proxy), không phải nhãn chuyên gia; ranh giới
    ML / DL / NLP vốn mờ nên nhầm lẫn giữa các lớp này là bình thường.
  - Tập nhỏ: kết quả có khoảng dao động lớn, chỉ có ý nghĩa tương đối.
  - Token theo khoảng trắng (âm tiết tiếng Việt), chưa tách từ; bigram bù một phần.
"""
import os
import re

SLUGS = {
    "machine_learning": "Machine Learning",
    "deep_learning": "Deep Learning",
    "nlp": "Natural Language Processing",
    "software": "Software Engineering & Web",
    "math": "Mathematics",
}


def label_from_folder(name):
    return SLUGS.get(name.lower(), name)


def chunk_text(text, words=150, min_words=40):
    """Cắt văn bản thành các đoạn ~words từ, ưu tiên cắt ở ranh giới đoạn/dòng trống.
    Đoạn cuối quá ngắn (< min_words) được gộp vào đoạn trước."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]
    chunks, cur, n = [], [], 0
    for p in paras:
        w = len(p.split())
        if cur and n + w > words:
            chunks.append(" ".join(cur))
            cur, n = [], 0
        cur.append(p)
        n += w
    if cur:
        if chunks and n < min_words:
            chunks[-1] += " " + " ".join(cur)
        else:
            chunks.append(" ".join(cur))
    return [c for c in chunks if len(c.split()) >= min_words // 2]


def load_dataset(root, words=150):
    """Trả về (texts, labels, groups). groups = '<nhãn>/<tên file>' để chia theo tài liệu."""
    if not os.path.isdir(root):
        raise FileNotFoundError(f"Không thấy thư mục dữ liệu: {root}")
    texts, labels, groups = [], [], []
    for folder in sorted(os.listdir(root)):
        fdir = os.path.join(root, folder)
        if not os.path.isdir(fdir):
            continue
        label = label_from_folder(folder)
        for fn in sorted(os.listdir(fdir)):
            if not fn.lower().endswith(".txt"):
                continue
            with open(os.path.join(fdir, fn), encoding="utf-8", errors="replace") as f:
                content = f.read()
            for c in chunk_text(content, words=words):
                texts.append(c)
                labels.append(label)
                groups.append(f"{folder}/{fn}")
    return texts, labels, groups


def build_model(kind="logreg"):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.pipeline import Pipeline

    vec = TfidfVectorizer(lowercase=True, ngram_range=(1, 2), sublinear_tf=True, min_df=1)
    if kind == "logreg":
        from sklearn.linear_model import LogisticRegression

        clf = LogisticRegression(max_iter=2000, class_weight="balanced")
    elif kind == "nb":
        from sklearn.naive_bayes import ComplementNB

        clf = ComplementNB()
    else:
        raise ValueError(f"kind không hợp lệ: {kind}")
    return Pipeline([("tfidf", vec), ("clf", clf)])


def save_model(model, path):
    import joblib

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    joblib.dump(model, path)


def load_model(path):
    import joblib

    return joblib.load(path) if os.path.exists(path) else None


def predict_domain(text, model):
    """(nhãn, độ tin cậy %). Độ tin cậy là xác suất của Logistic Regression, chưa hiệu chỉnh."""
    if not text or not text.strip() or model is None:
        return "Unknown", 0.0
    if hasattr(model, "predict_proba"):
        probs = model.predict_proba([text])[0]
        i = int(probs.argmax())
        return str(model.classes_[i]), round(float(probs[i]) * 100, 2)
    return str(model.predict([text])[0]), 0.0