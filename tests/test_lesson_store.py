import pytest

import lesson_store


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("LIBRARY_DB", str(tmp_path / "lib.db"))
    lesson_store.init()


def _result(summary="# Tiêu đề\n\n- Ý một\n- Ý hai " * 3):
    return {"domain": "CNTT", "conf": 90, "summary": summary, "terms": ["API"],
            "baseline": "b", "full_text": "f", "info": {"type": "PDF", "pages": 3, "chunks": 1},
            "warnings": [], "audio": b"khong-duoc-luu-vao-json"}


def test_save_and_get_roundtrip():
    lid = lesson_store.save_lesson("Bài 1", _result(), file_name="bai1.pdf")
    lesson = lesson_store.get_lesson(lid)
    assert lesson["title"] == "Bài 1"
    assert lesson["result"]["terms"] == ["API"]
    assert lesson["result"]["audio"] is None
    assert not lesson["has_audio"]
    assert lesson_store.get_audio(lid) is None


def test_audio_persists_as_bytes():
    lid = lesson_store.save_lesson("Bài 1", _result())
    data = bytes(range(256)) * 10
    lesson_store.set_audio(lid, data, "info")
    assert lesson_store.get_audio(lid) == data
    assert lesson_store.get_lesson(lid)["has_audio"]
    assert lesson_store.get_lesson(lid)["audio_info"] == "info"


def test_list_orders_by_last_opened_and_has_no_blob():
    a = lesson_store.save_lesson("A", _result())
    b = lesson_store.save_lesson("B", _result())
    lesson_store.set_audio(a, b"xx", "i")
    lesson_store.touch(a)
    items = lesson_store.list_lessons()
    assert [i["id"] for i in items][0] == a
    assert items[0]["has_audio"] and not items[1]["has_audio"]
    assert all("audio" not in i for i in items)
    assert "# " not in items[0]["summary_preview"]


def test_rename_and_delete():
    lid = lesson_store.save_lesson("Cũ", _result())
    assert lesson_store.rename(lid, "  Mới  ")
    assert lesson_store.get_lesson(lid)["title"] == "Mới"
    assert not lesson_store.rename(lid, "   ")
    lesson_store.delete(lid)
    assert lesson_store.get_lesson(lid) is None
    assert lesson_store.list_lessons() == []


def test_data_survives_new_connection():
    lid = lesson_store.save_lesson("Bền", _result())
    lesson_store.set_audio(lid, b"abc")
    # mỗi hàm mở kết nối mới, mô phỏng tắt/mở lại app
    assert lesson_store.get_audio(lid) == b"abc"
    assert lesson_store.get_lesson(lid)["title"] == "Bền"
