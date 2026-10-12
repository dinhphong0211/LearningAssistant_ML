"""Lưu bộ câu hỏi và lịch sử làm bài vào chính bài học (khóa "quiz" trong JSON của bài).

Dùng lại kết nối của lesson_store nên chạy được với cả SQLite và PostgreSQL, và vẫn lọc theo owner_id
(không đụng được bài của người khác). Không cần sửa lesson_store.
"""
import json
from datetime import datetime

import lesson_store


def _read(con, owner_id, lesson_id):
    row = con.execute("SELECT data FROM lessons WHERE id = ? AND owner_id = ?", (lesson_id, owner_id)).fetchone()
    return None if row is None else json.loads(row["data"])


def _write(con, owner_id, lesson_id, data):
    con.execute("UPDATE lessons SET data = ? WHERE id = ? AND owner_id = ?",
                (json.dumps(data, ensure_ascii=False), lesson_id, owner_id))


def load_quiz(owner_id, lesson_id):
    lesson_store._require_owner(owner_id)
    with lesson_store._conn() as con:
        data = _read(con, owner_id, lesson_id)
    return (data or {}).get("quiz")


def save_quiz(owner_id, lesson_id, questions, report):
    """Lưu bộ câu hỏi mới (xóa lịch sử cũ). Trả về False nếu không có bài/không thuộc owner."""
    lesson_store._require_owner(owner_id)
    with lesson_store._conn() as con:
        data = _read(con, owner_id, lesson_id)
        if data is None:
            return False
        data["quiz"] = {"questions": questions, "report": report, "history": [],
                        "created": datetime.now().isoformat(timespec="seconds")}
        _write(con, owner_id, lesson_id, data)
    return True


def add_attempt(owner_id, lesson_id, score, total, wrong):
    lesson_store._require_owner(owner_id)
    with lesson_store._conn() as con:
        data = _read(con, owner_id, lesson_id)
        if data is None or "quiz" not in data:
            return False
        data["quiz"].setdefault("history", []).append({
            "time": datetime.now().isoformat(timespec="seconds"),
            "score": score, "total": total, "wrong": list(wrong),
        })
        data["quiz"]["history"] = data["quiz"]["history"][-20:]
        _write(con, owner_id, lesson_id, data)
    return True
