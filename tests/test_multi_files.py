import pytest

from document.loader import load_document, load_documents, DocumentError, MAX_FILES


def _txt(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_single_file_same_as_load_document(tmp_path):
    p = _txt(tmp_path, "a.txt", "Đoạn một nói về học máy.\n\nĐoạn hai nói về dữ liệu.")
    one = load_documents([p])
    assert one.paragraphs == load_document(p).paragraphs      # không thêm tiêu đề
    assert one.sources[0]["name"] == "a.txt" and one.sources[0]["paragraphs"] == 2


def test_merge_keeps_order_and_adds_headings(tmp_path):
    a = _txt(tmp_path, "bai_mot.txt", "Nội dung bài một.")
    b = _txt(tmp_path, "bai_hai.txt", "Nội dung bài hai.\n\nThêm một đoạn.")
    doc = load_documents([a, (b, "Chương 2.txt")])
    assert doc.paragraphs[0] == "Tài liệu 1: bai mot."
    assert doc.paragraphs[1] == "Nội dung bài một."
    assert doc.paragraphs[2] == "Tài liệu 2: Chương 2."
    assert doc.paragraphs[-1] == "Thêm một đoạn."
    assert [s["name"] for s in doc.sources] == ["bai_mot.txt", "Chương 2.txt"]
    assert doc.source_type == "Gộp 2 file"


def test_headings_can_be_disabled(tmp_path):
    a = _txt(tmp_path, "a.txt", "Một.")
    b = _txt(tmp_path, "b.txt", "Hai.")
    assert load_documents([a, b], add_headings=False).paragraphs == ["Một.", "Hai."]


def test_duplicate_content_is_skipped_with_warning(tmp_path):
    a = _txt(tmp_path, "a.txt", "Cùng nội dung.")
    b = _txt(tmp_path, "b.txt", "Cùng nội dung.")
    c = _txt(tmp_path, "c.txt", "Nội dung khác hẳn.")
    doc = load_documents([a, b, c])
    assert [s["name"] for s in doc.sources] == ["a.txt", "c.txt"]
    assert any("trùng" in w and "b.txt" in w for w in doc.warnings)


def test_bad_file_among_good_is_skipped(tmp_path):
    good = _txt(tmp_path, "good.txt", "Nội dung tốt.")
    empty = tmp_path / "empty.txt"
    empty.write_bytes(b"")
    other = _txt(tmp_path, "good2.txt", "Nội dung tốt thứ hai.")
    doc = load_documents([good, str(empty), other])
    assert len(doc.sources) == 2
    assert any("empty.txt" in w for w in doc.warnings)


def test_all_bad_raises(tmp_path):
    empty = tmp_path / "empty.txt"
    empty.write_bytes(b"")
    weird = tmp_path / "x.xyz"
    weird.write_text("x")
    with pytest.raises(DocumentError):
        load_documents([str(empty), str(weird)])


def test_single_bad_file_raises_original_error(tmp_path):
    empty = tmp_path / "empty.txt"
    empty.write_bytes(b"")
    with pytest.raises(DocumentError):
        load_documents([str(empty)])


def test_too_many_files_and_empty_list(tmp_path):
    a = _txt(tmp_path, "a.txt", "Một.")
    with pytest.raises(DocumentError):
        load_documents([a] * (MAX_FILES + 1))
    with pytest.raises(DocumentError):
        load_documents([])


def test_pipeline_accepts_multiple_files(tmp_path):
    pytest.importorskip("google.generativeai")
    pytest.importorskip("numpy")
    from pipeline import run_pipeline, QUICK_LABEL

    class Fake:
        model = None
        last_used_model = "fake"

        def _generate(self, prompt):
            return "ok"

        def summarize_map_reduce(self, text, detail_level="standard"):
            self.seen = text
            return "Học máy dùng gradient descent."

    a = _txt(tmp_path, "a.txt", "Học máy là nhánh của trí tuệ nhân tạo. Mô hình dùng gradient descent để giảm hàm mất mát.")
    b = _txt(tmp_path, "b.txt", "Overfitting xảy ra khi mô hình quá khớp dữ liệu huấn luyện. Dropout giúp giảm overfitting.")
    fake = Fake()
    r = run_pipeline([a, (b, "Bài 2.txt")], fake, QUICK_LABEL)
    assert "Tài liệu 2: Bài 2." in fake.seen
    assert [s["name"] for s in r["sources"]] == ["a.txt", "Bài 2.txt"]
    assert r["info"]["files"] == 2
