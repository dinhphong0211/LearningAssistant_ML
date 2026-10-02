import re
from collections import Counter

# Xây dựng Domain Profile dạng giả lập từ vựng đặc trưng
DOMAIN_PROFILES = {
    "Machine Learning & AI": [
        "học máy", "trí tuệ nhân tạo", "machine learning", "artificial intelligence",
        "deep learning", "neural network", "thuật toán", "huấn luyện", "dataset",
        "mô hình", "svm", "backpropagation", "gradient descent", "tính toán"
    ],
    "Software Engineering & Web": [
        "lập trình", "phần mềm", "controller", "route", "framework", "laravel", 
        "php", "cấu trúc", "hàm", "action", "url", "dữ liệu", "database", "api",
        "frontend", "backend", "artisan", "visual studio code"
    ],
    "Mathematics": [
        "đạo hàm", "tích phân", "ma trận", "vector", "phương trình", "định lý",
        "xác suất", "thống kê", "giải tích", "đại số", "đồ thị"
    ]
}

def detect_domain(text, domain_profiles=DOMAIN_PROFILES):
    """
    Phân tích văn bản và nhận diện lĩnh vực dựa trên mật độ từ khóa.
    Input: Text đã được làm sạch (String).
    Output: Tuple (Domain_Name, Confidence_Score).
    """
    if not text:
        return "Unknown", 0.0

    # Chuyển văn bản về chữ thường để so khớp
    text_lower = text.lower()
    
    domain_scores = {}
    total_matches = 0

    # Tính điểm cho từng domain dựa trên số lượng từ khóa xuất hiện
    for domain, keywords in domain_profiles.items():
        score = 0
        for keyword in keywords:
            # Dùng regex để tìm chính xác từ khóa (word boundary)
            # Không dùng \b vì tiếng Việt có dấu khoảng trắng giữa các âm tiết
            # Ta dùng phương pháp đếm chuỗi con đơn giản cho MVP
            count = text_lower.count(keyword.lower())
            score += count
        
        domain_scores[domain] = score
        total_matches += score

    # Nếu không tìm thấy bất kỳ từ khóa nào
    if total_matches == 0:
        return "General/Unknown", 0.0

    # Tìm domain có điểm cao nhất
    best_domain = max(domain_scores, key=domain_scores.get)
    best_score = domain_scores[best_domain]
    
    # Tính độ tự tin (phần trăm)
    confidence = round((best_score / total_matches) * 100, 2)
    
    return best_domain, confidence

if __name__ == "__main__":
    # Test với đoạn văn bản em vừa trích xuất được từ PDF (Phase 5)
    sample_text = """
    PHẦN 1: KHỞI TẠO CONTROLLER BẰNG ARTISAN Trong hệ thống thực tế, chúng ta sẽ xây dựng chức năng Quản lý Sản phẩm (Product). Thay vì tạo file thủ công dễ gây lỗi cú pháp, chúng ta sẽ nhờ Laravel tự động sinh ra bộ khung chuẩn.
    Bước 1: Chạy lệnh tạo Controller – Tại cửa sổ Terminal của VS Code, bạn gõ lệnh sau và nhấn Enter:
    php artisan make:controller ProductController (Lưu ý: Nếu bạn đang dùng hệ thống giả lập Laravel Sail, hãy gõ ./vendor/bin/sail artisan make:controller ProductController)
    """
    
    print(f"Đang phân tích đoạn văn mẫu dài {len(sample_text)} ký tự...")
    detected_domain, conf = detect_domain(sample_text)
    print(f"==> Lĩnh vực được nhận diện: {detected_domain} (Độ tin cậy: {conf}%)")