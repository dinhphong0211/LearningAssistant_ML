import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import run_benchmark as rb   # noqa: E402

DOC1 = (
    "Học máy là nhánh của trí tuệ nhân tạo. Mô hình được huấn luyện bằng gradient descent để giảm hàm mất mát. "
    "Overfitting xảy ra khi mô hình quá khớp dữ liệu huấn luyện. Dropout giúp giảm overfitting trong mạng nơ-ron. "
    "Độ chính xác đạt 91 % sau 30 epoch trên tập kiểm tra. Cross-validation giúp đánh giá mô hình ổn định hơn. "
    "Tập dữ liệu lớn giúp mô hình tổng quát hóa tốt hơn trong thực tế."
)
REF1 = "Mô hình học máy được huấn luyện bằng gradient descent và dropout giúp giảm overfitting."


class FakeGemini:
    model = None
    last_used_model = "fake"
    model_name = "fake-model"

    def __init__(self):
        self.prompts = []

    def _generate(self, prompt):
        self.prompts.append(prompt)
        return "x"

    def summarize_map_reduce(self, text, detail_level="quick"):
        self._generate("TÓM TẮT")
        return "Mô hình học máy dùng gradient descent. Dropout giảm overfitting. Độ chính xác đạt 91 %. Câu thứ tư."


def _make(tmp_path, with_ref=True):
    d = tmp_path / "bench"
    d.mkdir()
    (d / "bai01.txt").write_text(DOC1, encoding="utf-8")
    if with_ref:
        (d / "bai01.ref.txt").write_text(REF1, encoding="utf-8")
    (d / "bai02.txt").write_text(DOC1.replace("91", "85"), encoding="utf-8")   # không có tham chiếu
    (d / "ghi_chu.xyz").write_text("bỏ qua", encoding="utf-8")                 # định dạng lạ
    return d


def test_find_cases_pairs_refs_and_skips_others(tmp_path):
    cases = rb.find_cases(_make(tmp_path))
    names = [(p.name, r.name if r else None) for p, r in cases]
    assert names == [("bai01.txt", "bai01.ref.txt"), ("bai02.txt", None)]


def test_textrank_only_run_writes_csv_and_means(tmp_path):
    res = rb.run_benchmark(_make(tmp_path), tmp_path / "out", n_sentences=2, log=lambda *_: None)
    methods = {r["method"] for r in res["rows"]}
    assert methods == {"TextRank", "TextRank + thuật ngữ"}
    with open(res["detail_csv"], encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 4 and set(rows[0]) >= set(rb.FIELDS)
    with_ref = [r for r in rows if r["doc"] == "bai01"]
    no_ref = [r for r in rows if r["doc"] == "bai02"]
    assert all(r["rouge1_f1"] != "" for r in with_ref)
    assert all(r["rouge1_f1"] == "" and r["has_reference"] == "0" for r in no_ref)
    s = {x["method"]: x for x in res["summary"]}
    assert s["TextRank"]["n_docs"] == 2 and s["TextRank"]["rouge1_f1_n"] == 1   # chỉ 1 tài liệu có tham chiếu
    assert (tmp_path / "out" / "summaries").glob("*.txt")


def test_gemini_path_with_guidance_and_truncation(tmp_path):
    fake = FakeGemini()
    res = rb.run_benchmark(_make(tmp_path), tmp_path / "out", n_sentences=2, summarizer=fake,
                           truncate_gemini=True, log=lambda *_: None)
    gem = [r for r in res["rows"] if r["method"].startswith("Gemini")]
    assert gem and gem[0]["method"] == "Gemini (cắt 2 câu)"
    assert fake.prompts and "Lưu ý bắt buộc" in fake.prompts[0]      # glossary đi kèm prompt
    assert res["info"]["gemini"] is True and res["info"]["gemini_model"] == "fake-model"


def test_bad_document_is_recorded_not_fatal(tmp_path):
    d = _make(tmp_path)
    (d / "hong.txt").write_text("", encoding="utf-8")                # rỗng -> lỗi
    res = rb.run_benchmark(d, tmp_path / "out", n_sentences=2, log=lambda *_: None)
    assert [e["doc"] for e in res["errors"]] == ["hong.txt"]
    assert {r["doc"] for r in res["rows"]} == {"bai01", "bai02"}


def test_ref_file_is_never_treated_as_document(tmp_path):
    d = tmp_path / "b"
    d.mkdir()
    (d / "a.txt").write_text(DOC1, encoding="utf-8")
    (d / "a.ref.txt").write_text(REF1, encoding="utf-8")
    assert [p.name for p, _ in rb.find_cases(d)] == ["a.txt"]
