from domain.lexicon import lexicon_terms, add_lexicon_terms
from domain.terminology import extract_terminology
from domain.term_cleaner import clean_terms

ML = ("Hồi quy tuyến tính là mô hình học máy. Hàm mất mát được tối thiểu hóa bằng gradient descent. "
      "Overfitting xảy ra khi mô hình quá khớp. Dropout và cross-validation giúp giảm overfitting.")


def test_finds_lowercase_domain_terms_the_regex_extractor_misses():
    regex_only = clean_terms(extract_terminology(ML), ML)
    assert "gradient descent" not in regex_only and "hàm mất mát" not in regex_only
    found = lexicon_terms(ML)
    assert "gradient descent" in found and "hàm mất mát" in found and "học máy" in found


def test_surface_form_prefers_lowercase_over_sentence_initial_capital():
    assert "overfitting" in lexicon_terms(ML)       # có cả "Overfitting" đầu câu và "overfitting" giữa câu


def test_acronym_keeps_uppercase_from_text():
    text = "Mạng CNN dùng convolution. CNN xử lý ảnh bằng backpropagation và relu trên gpu."
    assert "CNN" in lexicon_terms(text)


def test_merge_removes_case_duplicates_and_keeps_existing_display():
    merged = add_lexicon_terms(["Overfitting", "Batch Normalization"], ML)
    lowered = [t.lower() for t in merged]
    assert lowered.count("overfitting") == 1 and "Overfitting" in merged
    assert "Batch Normalization" in merged and "gradient descent" in merged


def test_unrelated_or_empty_text_gives_nothing():
    assert lexicon_terms("") == []
    assert lexicon_terms("Hôm nay trời đẹp, chúng ta đi dạo công viên.") == []


def test_only_dominant_domains_contribute():
    # văn bản nghiêng hẳn về ML: từ khóa web (php) chỉ xuất hiện 1 lần không được chen vào
    text = ML + " Ngoài lề có nhắc php một lần."
    assert "php" not in {t.lower() for t in lexicon_terms(text)}
