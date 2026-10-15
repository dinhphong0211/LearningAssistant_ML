import json
import random

import pytest

from quiz import generator as g

TEXT = (
    "Gradient descent là thuật toán tối ưu cập nhật tham số theo hướng giảm hàm mất mát của mô hình. "
    "Overfitting xảy ra khi mô hình ghi nhớ dữ liệu huấn luyện thay vì học quy luật tổng quát của dữ liệu. "
    "Dropout là kỹ thuật chính quy hóa bằng cách tắt ngẫu nhiên một số nơ-ron trong lúc huấn luyện mạng. "
    "Cross-validation chia dữ liệu thành nhiều phần để ước lượng sai số tổng quát một cách ổn định hơn. "
    "Learning rate quyết định bước nhảy của mỗi lần cập nhật tham số trong quá trình huấn luyện mô hình."
)
TERMS = ["gradient descent", "hàm mất mát", "overfitting", "dropout", "cross-validation", "learning rate",
         "Section", "app/Http/Controllers", "12"]
ABBR = {"CNN": "Convolutional Neural Network", "RNN": "Recurrent Neural Network",
        "LSTM": "Long Short-Term Memory", "GPU": "Graphics Processing Unit"}


def test_candidate_terms_filters_noise():
    out = g.candidate_terms(TERMS)
    assert "Section" not in out and "12" not in out and "app/Http/Controllers" not in out
    assert "dropout" in out


def test_local_cloze_questions_are_well_formed():
    qs = g.generate_local(TEXT, TERMS, ABBR, n=6, seed=1)
    assert qs
    for q in qs:
        assert len(q["options"]) == 4 and len({o.lower() for o in q["options"]}) == 4
        assert 0 <= q["answer"] < 4
        if q["type"] == "cloze":
            answer = q["options"][q["answer"]]
            assert "_____" in q["q"]
            assert answer.lower() not in q["q"].lower()      # đáp án không bị lộ trong câu hỏi
            assert answer.lower() in q["evidence"].lower()   # và có trong câu gốc


def test_local_abbreviation_question():
    qs = g.generate_local(TEXT, TERMS, ABBR, n=8, seed=3)
    ab = [q for q in qs if q["type"] == "abbreviation"]
    assert ab and ab[0]["options"][ab[0]["answer"]] in ABBR.values()


def test_local_is_deterministic_per_seed():
    a = g.generate_local(TEXT, TERMS, ABBR, n=5, seed=7)
    b = g.generate_local(TEXT, TERMS, ABBR, n=5, seed=7)
    assert a == b


def test_local_with_nothing_returns_empty():
    assert g.generate_local("Quá ngắn.", [], {}, n=5) == []


def _good(**kw):
    q = {"q": "Kỹ thuật nào tắt ngẫu nhiên một số nơ-ron khi huấn luyện?",
         "options": ["Dropout", "Pooling", "Softmax", "Sigmoid"], "answer": 0,
         "explain": "Dropout tắt ngẫu nhiên nơ-ron.",
         "evidence": "Dropout là kỹ thuật chính quy hóa bằng cách tắt ngẫu nhiên một số nơ-ron trong lúc huấn luyện mạng"}
    q.update(kw)
    return q


def test_parse_handles_markdown_fences():
    raw = "```json\n" + json.dumps([_good()], ensure_ascii=False) + "\n```"
    assert g.parse_quiz_json(raw)[0]["answer"] == 0


def test_validation_keeps_good_and_drops_bad():
    items = [
        _good(),
        _good(q="Câu bịa 1?", evidence="Transformer dùng cơ chế tự chú ý để xử lý chuỗi song song"),   # bằng chứng không có trong tài liệu
        _good(q="Câu bịa 2?", options=["Quantum", "Pooling", "Softmax", "Sigmoid"], answer=0),         # đáp án không có trong tài liệu
        _good(q="Câu 3?", options=["A", "A", "B", "C"]),                                               # đáp án trùng
        {"q": "thiếu khóa"},
        _good(),                                                                                        # trùng câu hỏi
    ]
    kept, dropped = g.validate_ai_questions(items, TEXT, random.Random(0))
    assert len(kept) == 1 and len(dropped) == 5
    q = kept[0]
    assert q["options"][q["answer"]] == "Dropout"     # đáp án vẫn đúng sau khi xáo vị trí
    assert q["source"] == "gemini"


class FakeAI:
    def __init__(self, payload=None, error=None):
        self.payload, self.error = payload, error

    def _generate(self, prompt):
        assert "Dựa CHỈ vào văn bản" in prompt
        if self.error:
            raise self.error
        return self.payload


def test_generate_quiz_uses_ai_then_fills_with_local():
    ai = FakeAI(json.dumps([_good()], ensure_ascii=False))
    qs, rep = g.generate_quiz(ai, TEXT, TERMS, ABBR, n=4, seed=2)
    assert len(qs) == 4 and rep["gemini"] == 1 and rep["offline"] == 3 and rep["error"] is None


def test_generate_quiz_survives_api_error_and_bad_json():
    qs, rep = g.generate_quiz(FakeAI(error=RuntimeError("429 quota")), TEXT, TERMS, ABBR, n=3)
    assert qs and rep["gemini"] == 0 and "429" in rep["error"]
    qs, rep = g.generate_quiz(FakeAI("không phải json"), TEXT, TERMS, ABBR, n=3)
    assert qs and rep["error"]


def test_generate_quiz_offline_mode_never_calls_ai():
    ai = FakeAI(error=AssertionError("không được gọi"))
    qs, rep = g.generate_quiz(ai, TEXT, TERMS, ABBR, n=3, use_ai=False)
    assert qs and rep["error"] is None


def test_storage_roundtrip_and_owner_isolation(tmp_path, monkeypatch):
    lesson_store = pytest.importorskip("lesson_store")
    from quiz import storage
    monkeypatch.setenv("LIBRARY_DB", str(tmp_path / "lib.db"))
    lesson_store.init()
    owner, other = "a" * 32, "b" * 32
    lid = lesson_store.save_lesson(owner, "Bài", {"domain": "x", "summary": "tóm tắt", "terms": []})
    qs = g.generate_local(TEXT, TERMS, ABBR, n=3)
    assert storage.save_quiz(owner, lid, qs, {"offline": 3})
    assert storage.load_quiz(owner, lid)["questions"] == qs
    assert lesson_store.get_lesson(owner, lid)["result"]["quiz"]["questions"] == qs
    assert storage.add_attempt(owner, lid, 2, 3, [1])
    assert storage.load_quiz(owner, lid)["history"][0]["score"] == 2
    # người khác không ghi/đọc được
    assert not storage.save_quiz(other, lid, [], {})
    assert storage.load_quiz(other, lid) is None
