from domain.term_cleaner import clean_terms

TEXT = (
    "Product Backlog là danh sách. Backlog được sắp xếp. Backlog thay đổi. "
    "Sprint kéo dài. Sprint mới. Sprint Review diễn ra. PBI và ROI. PBI nữa. "
    "Chúng ta viết code và design hằng ngày. Cần code sạch. Cần design tốt."
)


def test_merges_case_variants():
    out = clean_terms(["BACKLOG", "Backlog", "backlog"], TEXT)
    assert len(out) == 1 and out[0].lower() == "backlog"


def test_all_caps_long_word_becomes_title_case():
    out = clean_terms(["ARTIFACT"], "Artifact là sản phẩm. Artifact quan trọng.")
    assert out == ["Artifact"]


def test_keeps_short_acronyms():
    assert "PBI" in clean_terms(["PBI", "ROI"], TEXT)


def test_drops_stoplist_and_lowercase_common_words():
    out = clean_terms(["Code", "Design", "Sprint"], TEXT)
    assert "Code" not in out and "Design" not in out and "Sprint" in out


def test_drops_overlong_phrase():
    out = clean_terms(["Product Backlog Product Owner Sprint Goal"], TEXT)
    assert out == []


def test_keeps_multiword_terms():
    assert "Sprint Review" in clean_terms(["Sprint Review"], TEXT)
