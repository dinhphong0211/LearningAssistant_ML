from domain.formulas import extract_formulas, extract_units, looks_like_formula


def test_detects_plain_and_symbol_formulas():
    paras = ["y = Wx + b", "Loss = -Σ y log(p)", "accuracy = TP / (TP + FN)", "E = mc^2"]
    assert extract_formulas(paras) == paras


def test_sentence_with_equals_is_not_formula():
    assert not looks_like_formula("Trong đó x = 5 là giá trị đầu vào của mô hình")


def test_latex_span_extracted_without_surrounding_prose():
    out = extract_formulas(["Hàm kích hoạt $\\sigma(x)=\\frac{1}{1+e^{-x}}$ được dùng."])
    assert out == ["\\sigma(x)=\\frac{1}{1+e^{-x}}"]


def test_formulas_are_deduplicated_ignoring_spaces():
    assert extract_formulas(["y = Wx + b", "y=Wx+b"]) == ["y = Wx + b"]


def test_units():
    text = "Độ chính xác đạt 95 % với 16 GB RAM, 2,5 GHz, thời gian 20ms."
    assert extract_units(text) == ["95 %", "16 GB", "2,5 GHz", "20 ms"]


def test_ambiguous_units_ignored():
    assert extract_units("Có 5 m dây và 3 g muối, 7 s") == []


def test_empty():
    assert extract_formulas([]) == [] and extract_units("") == []
