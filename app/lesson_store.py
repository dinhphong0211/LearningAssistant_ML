"""Thư viện bài học: lưu bài đã tóm tắt và audio vào một file SQLite.

- Mỗi bài gồm kết quả phân tích (JSON) và file audio (BLOB, có thể chưa có).
- Vị trí đã nghe KHÔNG nằm ở đây mà nằm trong localStorage của trình duyệt
  (xem audio_player.py), vì trình phát chạy ở phía trình duyệt.
- Đường dẫn DB mặc định: <project>/data/library.db, đổi bằng biến môi trường
  LIBRARY_DB. Lưu ý: trên Streamlit Community Cloud ổ đĩa là tạm thời, file này
  sẽ mất khi app khởi động lại; muốn lưu lâu dài cần chạy app trên máy riêng/VPS
  hoặc đổi sang dịch vụ lưu trữ bên ngoài.
"""
import json
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "library.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS lessons (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    file_name TEXT,
    created_at TEXT NOT NULL,
    last_opened_at TEXT,
    domain TEXT,
    summary_preview TEXT,
    data TEXT NOT NULL,
    audio BLOB,
    audio_info TEXT,
    audio_updated_at TEXT
)
"""


def db_path():
    return Path(os.environ.get("LIBRARY_DB") or DEFAULT_DB)


@contextmanager
def _conn():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), timeout=10)
    con.row_factory = sqlite3.Row
    try:
        con.execute(_SCHEMA)
        yield con
        con.commit()
    finally:
        con.close()


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _preview(summary, limit=160):
    text = re.sub(r"[*_#`>\-]+", " ", summary or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def init():
    with _conn():
        pass


def save_lesson(title, result, file_name=None):
    """Lưu một bài mới (chưa có audio). Trả về id."""
    lesson_id = uuid.uuid4().hex[:12]
    payload = {k: v for k, v in result.items() if k != "audio"}
    with _conn() as con:
        con.execute(
            "INSERT INTO lessons (id, title, file_name, created_at, domain, summary_preview, data) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                lesson_id,
                (title or "Bài học").strip() or "Bài học",
                file_name,
                _now(),
                result.get("domain"),
                _preview(result.get("summary", "")),
                json.dumps(payload, ensure_ascii=False),
            ),
        )
    return lesson_id


def set_audio(lesson_id, audio_bytes, info=""):
    with _conn() as con:
        con.execute(
            "UPDATE lessons SET audio = ?, audio_info = ?, audio_updated_at = ? WHERE id = ?",
            (sqlite3.Binary(audio_bytes), info, _now(), lesson_id),
        )


def list_lessons():
    """Danh sách bài (không kèm audio), bài vừa mở/tạo gần nhất đứng đầu."""
    with _conn() as con:
        rows = con.execute(
            "SELECT id, title, file_name, created_at, last_opened_at, domain, summary_preview, "
            "audio IS NOT NULL AS has_audio, COALESCE(LENGTH(audio), 0) AS audio_bytes "
            "FROM lessons ORDER BY COALESCE(last_opened_at, created_at) DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_lesson(lesson_id):
    with _conn() as con:
        row = con.execute(
            "SELECT id, title, file_name, created_at, last_opened_at, audio_info, "
            "audio IS NOT NULL AS has_audio, data FROM lessons WHERE id = ?",
            (lesson_id,),
        ).fetchone()
    if row is None:
        return None
    out = dict(row)
    out["result"] = json.loads(out.pop("data"))
    out["result"]["audio"] = None
    return out


def get_audio(lesson_id):
    with _conn() as con:
        row = con.execute("SELECT audio FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
    if row is None or row["audio"] is None:
        return None
    return bytes(row["audio"])


def touch(lesson_id):
    with _conn() as con:
        con.execute("UPDATE lessons SET last_opened_at = ? WHERE id = ?", (_now(), lesson_id))


def rename(lesson_id, new_title):
    new_title = (new_title or "").strip()
    if not new_title:
        return False
    with _conn() as con:
        con.execute("UPDATE lessons SET title = ? WHERE id = ?", (new_title, lesson_id))
    return True


def delete(lesson_id):
    with _conn() as con:
        con.execute("DELETE FROM lessons WHERE id = ?", (lesson_id,))
