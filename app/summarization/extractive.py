import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import networkx as nx

# Tải gói dữ liệu tách câu của NLTK (chỉ chạy lần đầu)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
    nltk.download('punkt_tab')

def summarize_textrank_domain_aware(text, domain_terms, num_sentences=3):
    """
    Tóm tắt văn bản bằng TextRank có kết hợp trọng số thuật ngữ chuyên ngành.
    """
    if not text:
        return ""

    # 1. Tách văn bản thành các câu riêng biệt
    sentences = nltk.tokenize.sent_tokenize(text)
    
    # Nếu số câu trong bài ít hơn hoặc bằng số câu cần tóm tắt, trả về toàn bài
    if len(sentences) <= num_sentences:
        return text

    # 2. Vector hóa các câu bằng TF-IDF
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(sentences)

    # 3. Tính toán ma trận độ tương đồng Cosine giữa các câu
    similarity_matrix = cosine_similarity(tfidf_matrix)

    # 4. Xây dựng đồ thị và tính điểm TextRank
    nx_graph = nx.from_numpy_array(similarity_matrix)
    scores = nx.pagerank(nx_graph)

    # 5. Domain-aware Terminology Boost (Yếu tố chuyên ngành của đồ án)
    # Tăng điểm cho những câu chứa thuật ngữ từ Phase 7
    for i, sentence in enumerate(sentences):
        boost_multiplier = 0
        sentence_lower = sentence.lower()
        for term in domain_terms:
            if term.lower() in sentence_lower:
                # Tăng 15% điểm cho mỗi thuật ngữ quan trọng xuất hiện trong câu
                boost_multiplier += 0.15 
        
        # Áp dụng điểm thưởng
        scores[i] = scores[i] * (1 + boost_multiplier)

    # 6. Xếp hạng và chọn Top N câu cao điểm nhất
    # Lưu dưới dạng tuple (điểm số, index câu, nội dung câu)
    ranked_sentences = sorted(((scores[i], i, s) for i, s in enumerate(sentences)), reverse=True)
    
    # Lấy Top N câu
    top_n = ranked_sentences[:num_sentences]
    
    # 7. Sắp xếp lại Top N câu theo thứ tự xuất hiện ban đầu trong văn bản để giữ logic đọc
    top_n.sort(key=lambda x: x[1])
    
    # Ghép lại thành bản tóm tắt hoàn chỉnh
    summary = " ".join([s[2] for s in top_n])
    
    return summary

if __name__ == "__main__":
    # Dữ liệu test từ các Phase trước
    sample_text = """PHẦN 1: KHỞI TẠO CONTROLLER BẰNG ARTISAN Trong hệ thống thực tế, chúng ta sẽ xây dựng chức năng Quản lý Sản phẩm (Product). Thay vì tạo file thủ công dễ gây lỗi cú pháp, chúng ta sẽ nhờ Laravel tự động sinh ra bộ khung chuẩn.
Bước 1: Chạy lệnh tạo Controller – Tại cửa sổ Terminal của VS Code, bạn gõ lệnh sau và nhấn Enter:
php artisan make:controller ProductController (Lưu ý: Nếu bạn đang dùng hệ thống giả lập Laravel Sail, hãy gõ ./vendor/bin/sail artisan make:controller ProductController) Kết quả mong đợi: Terminal báo Controller created successfully.. Hệ thống đã tự động tạo ra một file mới tại đường dẫn: app/Http/Controllers/ProductController.php."""
    
    # Danh sách thuật ngữ lấy từ output Phase 7 của bạn
    sample_terms = [
        "ARTISAN", "CONTROLLER", "Code", "Controller", "Controllers", 
        "Enter", "Http", "Laravel", "Laravel Sail", "Product", 
        "ProductController", "Terminal", "VS", 
        "app/Http/Controllers/ProductController", "make:controller", "vendor/bin/sail"
    ]

    print("--- BẢN GỐC ---")
    print(sample_text)
    print("\n--- BẢN TÓM TẮT (BASELINE TEXTRANK + DOMAIN AWARE) ---")
    
    # Tóm tắt lấy 2 câu quan trọng nhất
    summary = summarize_textrank_domain_aware(sample_text, sample_terms, num_sentences=2)
    print(summary)