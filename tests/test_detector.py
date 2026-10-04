from domain.detector import detect_domain, detect_language, build_domain_profile, score_domains


def test_ml_text_detected():
    text = ("Học máy dùng gradient descent để giảm hàm mất mát. Overfitting xảy ra khi huấn luyện quá lâu, "
            "cần cross-validation và đo accuracy, precision, recall.")
    name, conf = detect_domain(text)
    assert name == "Machine Learning" and conf > 50


def test_deep_learning_text_detected():
    name, _ = detect_domain("Mạng neural network dùng convolution, relu và backpropagation trên gpu.")
    assert name == "Deep Learning"


def test_word_boundary_prevents_substring_matches():
    # 'api' nằm trong 'capital', 'rapid' nhưng không phải từ khóa API
    assert score_domains("The capital shows rapid growth.")["Software Engineering & Web"] == 0
    assert detect_domain("The capital shows rapid growth.") == ("General/Unknown", 0.0)


def test_empty_is_unknown():
    assert detect_domain("") == ("Unknown", 0.0)


def test_language_detection():
    assert detect_language("Đây là một đoạn văn bản tiếng Việt khá dài để kiểm tra việc nhận diện ngôn ngữ.") == "Vietnamese"
    assert detect_language("This is a long enough English sentence to test language detection here.") == "English"
    assert detect_language("ngắn") == "Unknown"


def test_profile_has_required_fields():
    text = "Học máy và overfitting. Overfitting là vấn đề. Mô hình học máy cần dữ liệu."
    p = build_domain_profile(text, ["Overfitting", "Học máy"], {"ML": "Machine Learning"}, ["y = Wx"], ["95 %"])
    for key in ("domain", "subdomain", "language", "technical_terms", "abbreviations",
                "important_concepts", "formulas", "units"):
        assert key in p
    assert p["domain"] == "Computer Science / AI"
    assert p["important_concepts"][0] in ("Overfitting", "Học máy")
