import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from preprocessing.chunker import chunk_text


def test_chunks_cover_whole_text_and_respect_limit():
    text = " ".join(f"Câu số {i} nói về học máy." for i in range(2000))
    chunks = chunk_text(text, max_chars=6000, overlap=300)
    assert len(chunks) > 1
    assert all(len(c) <= 6000 for c in chunks)
    assert "Câu số 0 " in chunks[0]
    assert "Câu số 1999" in chunks[-1]   # phần cuối không bị bỏ sót