from domain.abbreviation import (
    extract_abbreviations, find_undefined_abbreviations, abbreviation_conflicts,
)

TEXT = (
    "Artificial Intelligence (AI) là lĩnh vực rộng. Mạng Long Short-Term Memory (LSTM) xử lý chuỗi. "
    "CNN (Convolutional Neural Network) dùng cho ảnh. Natural Language Processing (NLP) rất phổ biến. "
    "GPU nhanh, GPU đắt. Xem hình (hình 3) và (tham khảo)."
)


def test_long_form_then_abbreviation():
    found = extract_abbreviations(TEXT)
    assert found["AI"] == "Artificial Intelligence"
    assert found["LSTM"] == "Long Short-Term Memory"
    assert found["NLP"] == "Natural Language Processing"


def test_abbreviation_then_long_form():
    assert extract_abbreviations(TEXT)["CNN"] == "Convolutional Neural Network"


def test_ignores_non_abbreviation_parentheses():
    found = extract_abbreviations(TEXT)
    assert set(found) == {"AI", "LSTM", "CNN", "NLP"}


def test_does_not_invent_expansion():
    # "AI" chỉ được mở rộng khi chính tài liệu định nghĩa
    assert extract_abbreviations("Chúng ta dùng AI rất nhiều. AI giúp ích.") == {}


def test_vietnamese_definition_not_matched_by_initials():
    assert extract_abbreviations("Trí tuệ nhân tạo (AI) đang phát triển.") == {}


def test_undefined_abbreviations_need_repetition():
    defined = extract_abbreviations(TEXT)
    assert find_undefined_abbreviations(TEXT, defined) == ["GPU"]


def test_conflict_detected():
    src = {"AI": "Artificial Intelligence"}
    conflicts = abbreviation_conflicts("Ambient Interface (AI) là khái niệm khác.", src)
    assert conflicts and conflicts[0]["abbreviation"] == "AI"
    assert abbreviation_conflicts("Artificial Intelligence (AI) là nền tảng.", src) == []


def test_empty():
    assert extract_abbreviations("") == {}
