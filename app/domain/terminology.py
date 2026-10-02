import re

def extract_terminology(text):
    """
    Trích xuất thuật ngữ, từ viết tắt và tên công nghệ từ văn bản tiếng Việt.
    """
    terms = set()
    
    if not text:
        return list(terms)

    # 1. Trích xuất từ viết tắt (Acronyms) - Chữ cái in hoa liền nhau (>= 2 ký tự)
    # VD: PHP, HTML, CSS, URL, API
    acronyms = re.findall(r'\b[A-Z]{2,}\b', text)
    terms.update(acronyms)
    
    # 2. Trích xuất CamelCase hoặc PascalCase (Tên class, biến trong code)
    # VD: ProductController, makeController
    camel_cases = re.findall(r'\b[A-Z]?[a-z]+[A-Z][a-z]*[A-Za-z]*\b', text)
    terms.update(camel_cases)

    # 3. Trích xuất cụm từ viết hoa chữ cái đầu (Tên công cụ, Framework)
    # VD: Laravel, Artisan, Controller, Visual Studio Code
    # Pattern: Bắt đầu bằng 1 chữ hoa, theo sau là chữ thường, có thể lặp lại cho cụm từ
    capitalized_phrases = re.findall(r'\b(?:[A-Z][a-z]+\s*)+\b', text)
    
    # Lọc các cụm từ viết hoa: Bỏ qua các từ quá ngắn hoặc có khả năng chỉ là từ đầu câu
    for phrase in capitalized_phrases:
        clean_phrase = phrase.strip()
        # Chỉ lấy các từ dài hơn 3 ký tự để tránh các từ đầu câu như "Trong", "Các", "Để"
        if len(clean_phrase) > 3 and clean_phrase.lower() not in ["trong", "bước", "phần", "nếu", "kết quả", "tại", "thay"]:
            terms.add(clean_phrase)

    # 4. Trích xuất các cấu trúc code có chứa ký tự đặc biệt như ':' hoặc '/'
    # VD: make:controller, app/Http/Controllers
    code_snippets = re.findall(r'\b[a-zA-Z0-9_]+[:/][a-zA-Z0-9_:/]+\b', text)
    terms.update(code_snippets)

    # Trả về danh sách đã sắp xếp
    return sorted(list(terms))

if __name__ == "__main__":
    # Test với đoạn văn bản của Lab Laravel
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