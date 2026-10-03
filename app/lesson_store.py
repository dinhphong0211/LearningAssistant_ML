"""Thư viện bài học: lưu bài đã tóm tắt và audio vào một file SQLite.

- Mỗi bài gồm kết quả phân tích (JSON) và file audio (BLOB, có thể chưa có).
- MỖI BÀI THUỘC VỀ MỘT owner_id (xem identity.py: mã ngẫu nhiên lưu trong cookie của
  từng trình duyệt). Mọi hàm đọc/ghi đều lọc theo owner_id nên máy nào chỉ thấy và chỉ
  sửa/xóa được bài do chính máy đó tạo, dù tất cả dùng chung một file DB trên server.
- Vị trí đã nghe KHÔNG nằm ở đây mà nằm trong localStorage của trình duyệt
  (xem audio_player.py), vì trình phát chạy ở phía trình duyệt.
- Đường dẫn DB mặc định: <project>/data/library.db, đổi bằng biến môi trường
  LIBRARY_DB. Lưu ý: trên Streamlit Community Cloud ổ đĩa là tạm thời, file này
  sẽ mất khi app khởi động lại; muốn lưu lâu dài cần chạy app trên máy riêng/VPS
  hoặc đổi sang dịch vụ lưu trữ bên ngoài.
- Bài cũ tạo trước khi có owner_id (owner_id NULL) không hiện với ai; dùng
  adopt_orphans(owner_id) để gán chúng cho một chủ.
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
    owner_id TEXT,
    title TEXT NOT NULL,
    file_name TEXT,
    created_at TEXT NOT NULL,
    last_opened_at TEXT,
    domain TEXT,
    summary_preview TEXT,
    mode TEXT,
    data TEXT NOT NULL,
    audio BLOB,
    audio_info TEXT,
    audio_updated_at TEXT
)
"""


def _ensure_schema(con):
    con.execute(_SCHEMA)
    # DB tạo từ phiên bản cũ chưa có cột owner_id -> thêm vào (bài cũ có owner_id NULL)
    cols = {r["name"] for r in con.execute("PRAGMA table_info(lessons)")}
    if "owner_id" not in cols:
        con.execute("ALTER TABLE lessons ADD COLUMN owner_id TEXT")
    if "mode" not in cols:  # 'summary' (tóm tắt) hoặc 'full' (đọc toàn bộ); bài cũ để NULL = tóm tắt
        con.execute("ALTER TABLE lessons ADD COLUMN mode TEXT")
    con.execute("CREATE INDEX IF NOT EXISTS idx_lessons_owner ON lessons(owner_id)")


def _require_owner(owner_id):
    # Không bao giờ để owner rỗng lọt vào truy vấn: sẽ khớp nhầm với bài chưa có chủ
    if not owner_id or not isinstance(owner_id, str):
        raise ValueError("owner_id là bắt buộc")
    return owner_id


def db_path():
    return Path(os.environ.get("LIBRARY_DB") or DEFAULT_DB)


@contextmanager
def _conn():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), timeout=10)
    con.row_factory = sqlite3.Row
    try:
        _ensure_schema(con)
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


def save_lesson(owner_id, title, result, file_name=None):
    """Lưu một bài mới (chưa có audio) cho owner_id. Trả về id."""
    _require_owner(owner_id)
    lesson_id = uuid.uuid4().hex[:12]
    payload = {k: v for k, v in result.items() if k != "audio"}
    with _conn() as con:
        con.execute(
            "INSERT INTO lessons (id, owner_id, title, file_name, created_at, domain, summary_preview, mode, data) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                lesson_id,
                owner_id,
                (title or "Bài học").strip() or "Bài học",
                file_name,
                _now(),
                result.get("domain"),
                _preview(result.get("summary", "")),
                result.get("mode") or "summary",
                json.dumps(payload, ensure_ascii=False),
            ),
        )
    return lesson_id


def set_audio(owner_id, lesson_id, audio_bytes, info=""):
    _require_owner(owner_id)
    with _conn() as con:
        con.execute(
            "UPDATE lessons SET audio = ?, audio_info = ?, audio_updated_at = ? "
            "WHERE id = ? AND owner_id = ?",
            (sqlite3.Binary(audio_bytes), info, _now(), lesson_id, owner_id),
        )


def list_lessons(owner_id):
    """Danh sách bài của owner_id (không kèm audio), bài vừa mở/tạo gần nhất đứng đầu."""
    _require_owner(owner_id)
    with _conn() as con:
        rows = con.execute(
            "SELECT id, title, file_name, created_at, last_opened_at, domain, summary_preview, mode, "
            "audio IS NOT NULL AS has_audio, COALESCE(LENGTH(audio), 0) AS audio_bytes "
            "FROM lessons WHERE owner_id = ? "
            "ORDER BY COALESCE(last_opened_at, created_at) DESC",
            (owner_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_lesson(owner_id, lesson_id):
    """Trả về None nếu bài không tồn tại HOẶC không thuộc owner_id này."""
    _require_owner(owner_id)
    with _conn() as con:
        row = con.execute(
            "SELECT id, title, file_name, created_at, last_opened_at, audio_info, "
            "audio IS NOT NULL AS has_audio, data FROM lessons WHERE id = ? AND owner_id = ?",
            (lesson_id, owner_id),
        ).fetchone()
    if row is None:
        return None
    out = dict(row)
    out["result"] = json.loads(out.pop("data"))
    out["result"]["audio"] = None
    return out


def get_audio(owner_id, lesson_id):
    _require_owner(owner_id)
    with _conn() as con:
        row = con.execute(
            "SELECT audio FROM lessons WHERE id = ? AND owner_id = ?", (lesson_id, owner_id)
        ).fetchone()
    if row is None or row["audio"] is None:
        return None
    return bytes(row["audio"])


def touch(owner_id, lesson_id):
    _require_owner(owner_id)
    with _conn() as con:
        con.execute(
            "UPDATE lessons SET last_opened_at = ? WHERE id = ? AND owner_id = ?",
            (_now(), lesson_id, owner_id),
        )


def rename(owner_id, lesson_id, new_title):
    _require_owner(owner_id)
    new_title = (new_title or "").strip()
    if not new_title:
        return False
    with _conn() as con:
        con.execute(
            "UPDATE lessons SET title = ? WHERE id = ? AND owner_id = ?",
            (new_title, lesson_id, owner_id),
        )
    return True


def delete(owner_id, lesson_id):
    _require_owner(owner_id)
    with _conn() as con:
        con.execute("DELETE FROM lessons WHERE id = ? AND owner_id = ?", (lesson_id, owner_id))


def adopt_orphans(owner_id):
    """Gán các bài cũ chưa có chủ (tạo trước khi có owner_id) cho owner_id. Trả về số bài."""
    _require_owner(owner_id)
    with _conn() as con:
        cur = con.execute("UPDATE lessons SET owner_id = ? WHERE owner_id IS NULL", (owner_id,))
        return cur.rowcount
