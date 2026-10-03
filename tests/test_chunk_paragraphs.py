from preprocessing.chunker import chunk_paragraphs


def test_lossless_no_overlap_and_limit():
    paras = [f"Đoạn {i}. " + "từ " * 200 for i in range(40)]
    chunks = chunk_paragraphs(paras, max_chars=3000)
    assert len(chunks) > 1 and all(len(c) <= 3000 for c in chunks)
    assert "\n\n".join(chunks).split() == "\n\n".join(paras).split()


def test_keeps_paragraph_boundaries():
    chunks = chunk_paragraphs(["Một.", "Hai.", "Ba."], max_chars=100)
    assert chunks == ["Một.\n\nHai.\n\nBa."]


def test_oversized_paragraph_is_split_without_loss():
    para = " ".join(f"Câu số {i} nói về học máy." for i in range(500))
    chunks = chunk_paragraphs([para], max_chars=2000)
    assert len(chunks) > 1 and all(len(c) <= 2000 for c in chunks)
    assert " ".join(chunks).split() == para.split()


def test_empty_input():
    assert chunk_paragraphs(["", "  ", None]) == []
