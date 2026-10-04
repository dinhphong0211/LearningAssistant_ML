import json

from pipeline import run_pipeline, QUICK_LABEL, DETAIL_LABEL, glossary_guide, with_guidance

DOC = """Giới thiệu về mạng nơ-ron

Convolutional Neural Network (CNN) là mô hình học sâu cho ảnh. Mạng CNN dùng convolution và relu, huấn luyện bằng backpropagation trên GPU. Natural Language Processing (NLP) dùng mô hình khác.

y = Wx + b

Mô hình đạt độ chính xác 91 % sau 30 epoch và dùng 16 GB bộ nhớ khi huấn luyện trên tập dữ liệu lớn. Overfitting được giảm bằng dropout. CNN vượt trội so với mạng truyền thẳng trong thí nghiệm này.
"""


class FakeSummarizer:
    model = None
    last_used_model = "fake-model"

    def __init__(self, summary):
        self.summary = summary
        self.prompts = []

    def _generate(self, prompt):
        self.prompts.append(prompt)
        return "ok"

    def summarize_map_reduce(self, text, detail_level="standard"):
        self._generate("TÓM TẮT: " + text[:40])
        return self.summary


def _run(tmp_path, summary, mode=QUICK_LABEL):
    f = tmp_path / "doc.txt"
    f.write_text(DOC, encoding="utf-8")
    fake = FakeSummarizer(summary)
    return fake, run_pipeline(str(f), fake, mode)


def test_specialized_fields_present(tmp_path):
    _, r = _run(tmp_path, "CNN đạt độ chính xác 91 % sau 30 epoch.")
    assert r["abbreviations"]["CNN"] == "Convolutional Neural Network"
    assert r["abbreviations"]["NLP"] == "Natural Language Processing"
    assert "y = Wx + b" in r["formulas"]
    assert "91 %" in r["units"] and "16 GB" in r["units"]
    assert r["profile"]["subdomain"] == "Deep Learning"
    assert r["profile"]["language"] == "Vietnamese"
    assert r["baseline_domain"]
    assert set(r["evaluation"]) == {"TextRank", "TextRank + thuật ngữ", "Gemini"}


def test_result_is_json_serializable(tmp_path):
    _, r = _run(tmp_path, "CNN đạt độ chính xác 91 %.")
    r.pop("audio")
    json.dumps(r)


def test_validation_flags_fabricated_number(tmp_path):
    _, ok = _run(tmp_path, "CNN đạt độ chính xác 91 % sau 30 epoch.")
    _, bad = _run(tmp_path, "CNN đạt độ chính xác 99 % sau 30 epoch.")
    assert not ok["validation"]["needs_review"]
    assert "99" in bad["validation"]["unsupported_numbers"]


def test_glossary_guide_reaches_every_prompt(tmp_path):
    fake, r = _run(tmp_path, "CNN đạt 91 %.")
    assert fake.prompts and "Convolutional Neural Network" in fake.prompts[0]
    assert "y = Wx + b" in fake.prompts[0]
    assert r["model_used"] == "fake-model"


def test_gemini_error_skips_validation(tmp_path):
    _, r = _run(tmp_path, "Lỗi khi gọi API Gemini: hết hạn mức")
    assert r["validation"] is None and r["evaluation"] is None


def test_with_guidance_does_not_mutate_shared_summarizer():
    fake = FakeSummarizer("x")
    guided = with_guidance(fake, "\n[GUIDE]")
    guided._generate("p")
    assert fake.prompts == ["p\n[GUIDE]"]
    assert "_generate" not in fake.__dict__        # đối tượng gốc không bị gắn đè
    assert with_guidance(fake, "") is fake


def test_glossary_guide_empty_when_nothing_to_say():
    assert glossary_guide([], {}, []) == ""
