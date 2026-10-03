import pytest

from preprocessing.boilerplate import (
    is_page_number, filter_pdf_furniture, strip_repeated_page_lines, drop_page_number_paragraphs,
)


@pytest.mark.parametrize("line", ["12", " - 12 - ", "[7]", "Trang 12", "trang 3 / 10", "Page 3 of 10", "p. 5", "3/10", "tr.4"])
def test_page_numbers_recognised(line):
    assert is_page_number(line)


@pytest.mark.parametrize("line", ["", "Năm 2024", "2024", "Chương 3", "Có 12 mô hình", "Mục 1.2", "12 con voi", "page"])
def test_real_content_is_not_page_number(line):
    assert not is_page_number(line)


def test_strict_ignores_bare_numbers():
    assert not is_page_number("12", strict=True)
    assert is_page_number("Trang 12", strict=True)


# block PyMuPDF: (x0, y0, x1, y1, text, block_no, block_type)
def _page(n, h=800, body="Nội dung chính của trang."):
    return (h, [
        (50, 20, 500, 40, "Báo cáo thường niên ABC", 0, 0),          # header (mép trên, lặp lại)
        (50, 100, 500, 200, f"{body} {n}", 1, 0),                     # thân
        (50, 760, 500, 780, f"Trang {n}", 2, 0),                      # footer: số trang
    ])


def test_pdf_removes_repeated_header_and_page_numbers_only():
    pages = [_page(i) for i in range(1, 7)]
    kept = filter_pdf_furniture(pages)
    texts = [b[4] for b in kept]
    assert len(kept) == 6
    assert all(t.startswith("Nội dung chính") for t in texts)


def test_pdf_keeps_unique_text_in_margin_and_body_numbers():
    pages = [_page(i) for i in range(1, 7)]
    # tiêu đề chỉ có ở trang 1 (nằm sát mép trên) -> không lặp -> phải giữ
    pages[0][1].append((50, 5, 500, 25, "Tiêu đề riêng của tài liệu", 3, 0))
    # số đứng riêng GIỮA trang không phải số trang -> giữ
    pages[2][1].append((50, 400, 80, 420, "42", 4, 0))
    texts = [b[4] for b in filter_pdf_furniture(pages)]
    assert "Tiêu đề riêng của tài liệu" in texts
    assert "42" in texts


def test_pdf_short_doc_only_drops_page_numbers():
    pages = [_page(1), _page(2)]  # < 3 trang: không đủ cơ sở coi header là lặp lại
    texts = [b[4] for b in filter_pdf_furniture(pages)]
    assert texts.count("Báo cáo thường niên ABC") == 2
    assert not any(t.startswith("Trang") for t in texts)


def test_pdf_drops_image_blocks():
    pages = [(800, [(0, 100, 10, 110, "<image: x>", 0, 1), (0, 200, 10, 210, "Văn bản", 1, 0)])] * 3
    assert [b[4] for b in filter_pdf_furniture(pages)] == ["Văn bản"] * 3


def test_ocr_pages_repeated_edge_lines_removed():
    topics = ["mạng nơ-ron", "cây quyết định", "hồi quy", "phân cụm", "học tăng cường"]
    pages = []
    for i, t in enumerate(topics, 1):
        body = "\n".join(f"Dòng thân số {k} bàn về {t}." for k in range(6))
        pages.append(f"CÔNG TY ABC - BÁO CÁO\n{body}\nCâu kết riêng của {t}.\n- {i} -")
    out = strip_repeated_page_lines(pages)
    assert all("CÔNG TY ABC" not in p for p in out)
    assert all(f"- {i} -" not in p for i, p in enumerate(out, 1))
    assert all(f"Câu kết riêng của {t}." in p and "Dòng thân số 0" in p for t, p in zip(topics, out))


def test_ocr_keeps_repeated_line_in_body_middle():
    body = "\n".join(["Dòng a.", "Dòng b.", "Dòng c.", "Dòng d.", "Giữa trang lặp", "Dòng e.", "Dòng f.", "Dòng g.", "Dòng h."])
    out = strip_repeated_page_lines([body] * 4)
    assert all("Giữa trang lặp" in p for p in out)


def test_drop_page_number_paragraphs():
    paras = ["Đoạn một.", "12", "Trang 13", "Đoạn hai\nTrang 5\ncòn tiếp.", "Năm 2024"]
    assert drop_page_number_paragraphs(paras) == ["Đoạn một.", "Đoạn hai\ncòn tiếp.", "Năm 2024"]
