import re

# Từ đệm / từ chức năng hay đứng đầu câu hoặc đi kèm danh từ, không phải thuật ngữ.
# Cũng gồm nhãn cấu trúc sách ("Section", "Fig", "Table"...).
_STOP = {
    "trong", "các", "những", "một", "để", "của", "và", "với", "cho", "khi", "nếu", "này", "đó",
    "bước", "phần", "kết", "quả", "tại", "thay", "chúng", "ta", "bạn", "hãy", "như", "theo",
    "mục", "chương", "hình", "bảng", "ví", "dụ", "lưu", "ý", "vì", "do", "thì", "mà", "cũng",
    "section", "fig", "figure", "table", "chapter", "exercises", "summary", "the", "a", "an",
}

# Một token là một cụm chữ cái (kể cả có dấu tiếng Việt) hoặc một dấu kết thúc câu / xuống dòng
_TOKEN = re.compile(r"[^\W\d_]+|[.!?:;\n]")


def _capitalized_phrases(text):
    """Cụm từ viết hoa chữ đầu (Laravel Sail, Visual Studio Code...).

    Khác regex cũ: tách theo token nên (1) nhận chữ hoa có dấu, (2) cắt cụm tại từ đệm như
    "Trong", "Section", (3) bỏ từ đơn chỉ viết hoa vì đứng đầu câu.
    """
    out, run = [], []   # run: danh sách (từ, đứng_đầu_câu)
    at_start = True

    def flush():
        if run and not (len(run) == 1 and run[0][1]):
            out.append(" ".join(w for w, _ in run))
        run.clear()

    for tok in _TOKEN.findall(text):
        if tok in ".!?:;\n":
            flush()
            at_start = True
            continue
        if len(tok) > 1 and tok[0].isupper() and tok[1:].islower() and tok.lower() not in _STOP:
            run.append((tok, at_start))
        else:
            flush()
        at_start = False
    flush()
    return out


def extract_terminology(text):
    """
    Trích xuất thuật ngữ, từ viết tắt và tên công nghệ từ văn bản tiếng Việt.
    """
    terms = set()

    if not text:
        return list(terms)

    # 1. Từ viết tắt (Acronyms) - chữ in hoa liền nhau (>= 2 ký tự). VD: PHP, HTML, CSS, URL, API
    acronyms = re.findall(r'\b[A-Z]{2,}\b', text)
    terms.update(acronyms)

    # 2. CamelCase / PascalCase (tên class, biến trong code). VD: ProductController, makeController
    camel_cases = re.findall(r'\b[A-Z]?[a-z]+[A-Z][a-z]*[A-Za-z]*\b', text)
    terms.update(camel_cases)

    # 3. Cụm từ viết hoa chữ đầu (tên công cụ, framework). VD: Laravel, Artisan, Visual Studio Code
    for phrase in _capitalized_phrases(text):
        if len(phrase) > 3:
            terms.add(phrase)

    # 4. Cấu trúc code có ':' hoặc '/'. VD: make:controller, app/Http/Controllers
    code_snippets = re.findall(r'\b[a-zA-Z0-9_]+[:/][a-zA-Z0-9_:/]+\b', text)
    terms.update(code_snippets)

    return sorted(list(terms))

if __name__ == "__main__":
    sample_text = """
    PHẦN 1: KHỞI TẠO CONTROLLER BẰNG ARTISAN Trong hệ thống thực tế, chúng ta sẽ xây dựng chức năng Quản lý Sản phẩm (Product). Thay vì tạo file thủ công dễ gây lỗi cú pháp, chúng ta sẽ nhờ Laravel tự động sinh ra bộ khung chuẩn.
    Bước 1: Chạy lệnh tạo Controller – Tại cửa sổ Terminal của VS Code, bạn gõ lệnh sau và nhấn Enter:
    php artisan make:controller ProductController (Lưu ý: Nếu bạn đang dùng hệ thống giả lập Laravel Sail, hãy gõ ./vendor/bin/sail artisan make:controller ProductController)
    Kết quả mong đợi: Terminal báo Controller created successfully.. Hệ thống đã tự động tạo ra một file mới tại đường dẫn: app/Http/Controllers/ProductController.php.
    """

    print("--- ĐANG TRÍCH XUẤT THUẬT NGỮ ---")
    extracted_terms = extract_terminology(sample_text)

    print(f"Tìm thấy {len(extracted_terms)} thuật ngữ / từ khóa công nghệ:")
    for term in extracted_terms:
        print(f" - {term}")
