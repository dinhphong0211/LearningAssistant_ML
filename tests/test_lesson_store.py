import pytest

import lesson_store

OWNER = "a" * 32
OTHER = "b" * 32


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("LIBRARY_DB", str(tmp_path / "lib.db"))
    lesson_store.init()


def _result(summary="# Tiêu đề\n\n- Ý một\n- Ý hai " * 3):
    return {"domain": "CNTT", "conf": 90, "summary": summary, "terms": ["API"],
            "baseline": "b", "full_text": "f", "info": {"type": "PDF", "pages": 3, "chunks": 1},
            "warnings": [], "audio": b"khong-duoc-luu-vao-json"}


def test_save_and_get_roundtrip():
    lid = lesson_store.save_lesson(OWNER, "Bài 1", _result(), file_name="bai1.pdf")
    lesson = lesson_store.get_lesson(OWNER, lid)
    assert lesson["title"] == "Bài 1"
    assert lesson["result"]["terms"] == ["API"]
    assert lesson["result"]["audio"] is None
    assert not lesson["has_audio"]
    assert lesson_store.get_audio(OWNER, lid) is None


def test_audio_persists_as_bytes():
    lid = lesson_store.save_lesson(OWNER, "Bài 1", _result())
    data = bytes(range(256)) * 10
    lesson_store.set_audio(OWNER, lid, data, "info")
    assert lesson_store.get_audio(OWNER, lid) == data
    assert lesson_store.get_lesson(OWNER, lid)["has_audio"]
    assert lesson_store.get_lesson(OWNER, lid)["audio_info"] == "info"


def test_list_orders_by_last_opened_and_has_no_blob():
    a = lesson_store.save_lesson(OWNER, "A", _result())
    b = lesson_store.save_lesson(OWNER, "B", _result())
    lesson_store.set_audio(OWNER, a, b"xx", "i")
    lesson_store.touch(OWNER, a)
    items = lesson_store.list_lessons(OWNER)
    assert [i["id"] for i in items][0] == a
    assert items[0]["has_audio"] and not items[1]["has_audio"]
    assert all("audio" not in i for i in items)
    assert "# " not in items[0]["summary_preview"]


def test_rename_and_delete():
    lid = lesson_store.save_lesson(OWNER, "Cũ", _result())
    assert lesson_store.rename(OWNER, lid, "  Mới  ")
    assert lesson_store.get_lesson(OWNER, lid)["title"] == "Mới"
    assert not lesson_store.rename(OWNER, lid, "   ")
    lesson_store.delete(OWNER, lid)
    assert lesson_store.get_lesson(OWNER, lid) is None
    assert lesson_store.list_lessons(OWNER) == []


def test_data_survives_new_connection():
    lid = lesson_store.save_lesson(OWNER, "Bền", _result())
    lesson_store.set_audio(OWNER, lid, b"abc")
    # mỗi hàm mở kết nối mới, mô phỏng tắt/mở lại app
    assert lesson_store.get_audio(OWNER, lid) == b"abc"
    assert lesson_store.get_lesson(OWNER, lid)["title"] == "Bền"


# ---------- Cô lập dữ liệu giữa các trình duyệt ----------
def test_other_owner_cannot_see_or_touch_lesson():
    lid = lesson_store.save_lesson(OWNER, "Riêng tư", _result())
    lesson_store.set_audio(OWNER, lid, b"mp3", "i")

    assert lesson_store.list_lessons(OTHER) == []
    assert lesson_store.get_lesson(OTHER, lid) is None
    assert lesson_store.get_audio(OTHER, lid) is None

    # sửa / xóa / ghi audio bằng id của người khác phải không có tác dụng
    lesson_store.rename(OTHER, lid, "Bị đổi tên")
    lesson_store.touch(OTHER, lid)
    lesson_store.set_audio(OTHER, lid, b"hack", "x")
    lesson_store.delete(OTHER, lid)

    lesson = lesson_store.get_lesson(OWNER, lid)
    assert lesson is not None
    assert lesson["title"] == "Riêng tư"
    assert lesson["last_opened_at"] is None
    assert lesson_store.get_audio(OWNER, lid) == b"mp3"


def test_each_owner_lists_only_own_lessons():
    a = lesson_store.save_lesson(OWNER, "A", _result())
    b = lesson_store.save_lesson(OTHER, "B", _result())
    assert [x["id"] for x in lesson_store.list_lessons(OWNER)] == [a]
    assert [x["id"] for x in lesson_store.list_lessons(OTHER)] == [b]


def test_owner_id_is_required():
    for bad in (None, "", 123):
        with pytest.raises(ValueError):
            lesson_store.list_lessons(bad)
        with pytest.raises(ValueError):
            lesson_store.save_lesson(bad, "x", _result())


def test_migrates_old_db_and_hides_orphans(tmp_path, monkeypatch):
    import sqlite3
    old = tmp_path / "old.db"
    con = sqlite3.connect(old)
    con.execute(
        "CREATE TABLE lessons (id TEXT PRIMARY KEY, title TEXT NOT NULL, file_name TEXT, "
        "created_at TEXT NOT NULL, last_opened_at TEXT, domain TEXT, summary_preview TEXT, "
        "data TEXT NOT NULL, audio BLOB, audio_info TEXT, audio_updated_at TEXT)"
    )
    con.execute("INSERT INTO lessons (id, title, created_at, data) VALUES ('old1', 'Bài cũ', '2026-01-01T00:00:00', '{}')")
    con.commit()
    con.close()

    monkeypatch.setenv("LIBRARY_DB", str(old))
    lesson_store.init()
    assert lesson_store.list_lessons(OWNER) == []      # bài cũ không lộ cho ai
    assert lesson_store.adopt_orphans(OWNER) == 1      # nhưng gán lại được cho một chủ
    assert [x["id"] for x in lesson_store.list_lessons(OWNER)] == ["old1"]
    assert lesson_store.list_lessons(OTHER) == []
    assert lesson_store.adopt_orphans(OTHER) == 0


def test_mode_is_stored_and_listed():
    full = lesson_store.save_lesson(OWNER, "Toàn văn", {**_result(), "mode": "full"})
    old = lesson_store.save_lesson(OWNER, "Tóm tắt", _result())   # không có khóa mode -> 'summary'
    modes = {i["id"]: i["mode"] for i in lesson_store.list_lessons(OWNER)}
    assert modes == {full: "full", old: "summary"}
    assert lesson_store.get_lesson(OWNER, full)["result"]["mode"] == "full"
