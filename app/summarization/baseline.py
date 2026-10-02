"""Baseline tóm tắt trích xuất (extractive): TF-IDF + cosine similarity + TextRank.

Ý tưởng (Mihalcea & Tarau, 2004):
  1. Mỗi câu là một đỉnh của đồ thị.
  2. Cạnh nối hai câu có trọng số = độ tương đồng cosine giữa vector TF-IDF của chúng.
  3. Chạy PageRank: câu được nhiều câu "quan trọng" khác giống nó thì điểm cao.
  4. Lấy top-N câu, xếp lại theo thứ tự xuất hiện trong tài liệu.

Không cần huấn luyện, không cần GPU, không gọi API. Đây là mốc so sánh cho mô hình Gemini.
"""
import math
import re
from collections import Counter

import numpy as np

_STOPWORDS = set("""
và là của các có cho với trong được một những này đó khi để từ như không cũng đã sẽ
rằng thì mà hay hoặc nên vì nếu tại theo về ra vào lên bởi còn rất nhiều
the a an of and or to in on for with is are was were be been as by at from that this it its
""".split())

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_TOKEN = re.compile(r"\w+", re.UNICODE)


def split_sentences(text):
    sents = [s.strip() for s in _SENT_SPLIT.split(text or "")]
    return [s for s in sents if len(_TOKEN.findall(s)) >= 4]


def _tokens(sentence):
    return [t for t in _TOKEN.findall(sentence.lower()) if t not in _STOPWORDS and len(t) > 1]


def _tfidf_matrix(sentences):
    docs = [_tokens(s) for s in sentences]
    vocab = {w: i for i, w in enumerate(sorted({w for d in docs for w in d}))}
    n = len(docs)
    df = Counter(w for d in docs for w in set(d))
    mat = np.zeros((n, len(vocab)))
    for i, d in enumerate(docs):
        for w, c in Counter(d).items():
            idf = math.log((1 + n) / (1 + df[w])) + 1
            mat[i, vocab[w]] = c * idf
    return mat


def _cosine_matrix(mat):
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    unit = mat / norms
    sim = unit @ unit.T
    np.fill_diagonal(sim, 0.0)
    return sim


def _pagerank(sim, damping=0.85, iters=100, tol=1e-6):
    n = sim.shape[0]
    row_sum = sim.sum(axis=1, keepdims=True)
    row_sum[row_sum == 0] = 1.0
    trans = (sim / row_sum).T            # cột j: phân phối điểm từ câu j sang các câu khác
    scores = np.full(n, 1.0 / n)
    for _ in range(iters):
        new = (1 - damping) / n + damping * trans @ scores
        if np.abs(new - scores).sum() < tol:
            scores = new
            break
        scores = new
    return scores


def textrank_summarize(text, n_sentences=5, max_sentences_considered=2000):
    """Trả về bản tóm tắt gồm n_sentences câu quan trọng nhất (theo thứ tự gốc)."""
    sentences = split_sentences(text)[:max_sentences_considered]
    if not sentences:
        return (text or "").strip()
    if len(sentences) <= n_sentences:
        return " ".join(sentences)

    sim = _cosine_matrix(_tfidf_matrix(sentences))
    scores = _pagerank(sim)
    top = sorted(np.argsort(-scores)[:n_sentences])
    return " ".join(sentences[i] for i in top)
