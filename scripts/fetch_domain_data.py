"""Tải 28 mục D2L tiếng Việt (vi.d2l.ai) về data/domain/<nhãn>/*.txt.

Chạy:  python scripts/fetch_domain_data.py
Chỉ dùng thư viện chuẩn. Cần có mạng. Nguồn: https://vi.d2l.ai (CC BY-SA 4.0, cần ghi nguồn).

CẢNH BÁO: bộ trích văn bản chưa được thử trên trang thật (môi trường tác giả không có mạng).
Sau khi chạy, mở vài file .txt kiểm tra: không lẫn mục lục sách, đủ dài (script in số từ).
Nếu một file quá ngắn hoặc lẫn mục lục, mở trang trong trình duyệt, Ctrl+A, Ctrl+C, dán vào file.
Công thức toán thường bị mất khi lấy từ HTML (giới hạn đã biết).
"""
import os
import re
import sys
import urllib.request
from html.parser import HTMLParser

BASE = "https://vi.d2l.ai/"
SECTIONS = {
    "machine_learning": [
        ("4_4_underfit_overfit", "chapter_multilayer-perceptrons/underfit-overfit.html"),
        ("4_5_weight_decay", "chapter_multilayer-perceptrons/weight-decay.html"),
        ("4_9_distribution_shift", "chapter_multilayer-perceptrons/environment.html"),
        ("4_6_dropout", "chapter_multilayer-perceptrons/dropout.html"),
        ("4_8_numerical_stability_init", "chapter_multilayer-perceptrons/numerical-stability-and-init.html"),
        ("4_10_kaggle_house_price", "chapter_multilayer-perceptrons/kaggle-house-price.html"),
        ("11_3_gradient_descent", "chapter_optimization/gd.html"),
    ],
    "deep_learning": [
        ("4_7_backprop", "chapter_multilayer-perceptrons/backprop.html"),
        ("6_1_why_conv", "chapter_convolutional-neural-networks/why-conv.html"),
        ("7_5_batch_norm", "chapter_convolutional-modern/batch-norm.html"),
        ("6_5_pooling", "chapter_convolutional-neural-networks/pooling.html"),
        ("6_6_lenet", "chapter_convolutional-neural-networks/lenet.html"),
        ("7_1_alexnet", "chapter_convolutional-modern/alexnet.html"),
        ("7_6_resnet", "chapter_convolutional-modern/resnet.html"),
    ],
    "nlp": [
        ("8_3_language_models", "chapter_recurrent-neural-networks/language-models-and-dataset.html"),
        ("14_1_word2vec", "chapter_natural-language-processing-pretraining/word2vec.html"),
        ("15_1_sentiment", "chapter_natural-language-processing-applications/sentiment-analysis-and-dataset.html"),
        ("8_2_text_preprocessing", "chapter_recurrent-neural-networks/text-preprocessing.html"),
        ("14_6_subword_embedding", "chapter_natural-language-processing-pretraining/subword-embedding.html"),
        ("14_8_bert", "chapter_natural-language-processing-pretraining/bert.html"),
        ("15_4_nli_dataset", "chapter_natural-language-processing-applications/natural-language-inference-and-dataset.html"),
    ],
    "math": [
        ("2_4_calculus", "chapter_preliminaries/calculus.html"),
        ("2_6_probability", "chapter_preliminaries/probability.html"),
        ("18_5_integral_calculus", "chapter_appendix-mathematics-for-deep-learning/integral-calculus.html"),
        ("2_3_linear_algebra", "chapter_preliminaries/linear-algebra.html"),
        ("18_2_eigendecomposition", "chapter_appendix-mathematics-for-deep-learning/eigendecomposition.html"),
        ("18_6_random_variables", "chapter_appendix-mathematics-for-deep-learning/random-variables.html"),
        ("18_10_information_theory", "chapter_appendix-mathematics-for-deep-learning/information-theory.html"),
    ],
}

_SKIP_TAGS = {"script", "style", "nav", "header", "footer", "aside", "button", "noscript", "svg", "form"}
_SKIP_CLASS = re.compile(r"sidebar|toc|navigation|nav-|navbar|related|footer|headerlink|menu|search", re.I)
_BLOCK = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "pre", "tr", "section", "table"}
_NOISE = re.compile(r"^(copy to clipboard|mxnet|pytorch|tensorflow|jax|discussions?|\u00b6)$", re.I)


class _Extract(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth_skip = 0
        self.stack = []  # mỗi phần tử: có bị bỏ qua không
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ("br", "img", "hr", "meta", "link", "input"):
            if tag == "br":
                self.parts.append("\n")
            return
        a = dict(attrs)
        skip = tag in _SKIP_TAGS or bool(_SKIP_CLASS.search((a.get("class") or "") + " " + (a.get("id") or "")))
        self.stack.append(skip)
        if skip:
            self.depth_skip += 1
        if tag in _BLOCK and not self.depth_skip:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("br", "img", "hr", "meta", "link", "input") or not self.stack:
            return
        if self.stack.pop():
            self.depth_skip -= 1
        if tag in _BLOCK and not self.depth_skip:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.depth_skip:
            self.parts.append(data)


def html_to_text(html):
    p = _Extract()
    p.feed(html)
    lines = [re.sub(r"[ \t\u00a0]+", " ", l).strip() for l in "".join(p.parts).split("\n")]
    out, blank = [], 0
    for l in lines:
        if _NOISE.match(l):
            continue
        if not l:
            blank += 1
            if blank == 1:
                out.append("")
            continue
        blank = 0
        out.append(l)
    return "\n".join(out).strip() + "\n"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (student ML project; fetch 28 pages)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def main():
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "domain")
    fails = 0
    for label, items in SECTIONS.items():
        os.makedirs(os.path.join(root, label), exist_ok=True)
        for name, path in items:
            try:
                text = html_to_text(fetch(BASE + path))
            except Exception as e:  # noqa: BLE001
                print(f"[LỖI] {label}/{name}: {e}")
                fails += 1
                continue
            n = len(text.split())
            out = os.path.join(root, label, name + ".txt")
            with open(out, "w", encoding="utf-8") as f:
                f.write(text)
            flag = "" if n >= 300 else "  <-- QUÁ NGẮN, kiểm tra tay"
            print(f"{label}/{name}.txt  {n} từ{flag}")
    if fails:
        print(f"\n{fails} mục tải lỗi (xem dòng [LỖI] ở trên). Kiểm tra mạng rồi chạy lại.")
    else:
        print("\nXong. Mở vài file kiểm tra có lẫn mục lục không. Ghi nguồn + giấy phép vào data/README.md.")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()