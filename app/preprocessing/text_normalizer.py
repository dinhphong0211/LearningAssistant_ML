import unicodedata
import re

def normalize_vietnamese_text(text):
    """
    Chuẩn hóa văn bản tiếng Việt về chuẩn Unicode NFC.
    Loại bỏ các ký tự rác và khoảng trắng dư thừa.
    """
    if not text:
        return ""

    # 1. Chuẩn hóa Unicode (Đưa tất cả về chuẩn Dựng sẵn NFC)
    text = unicodedata.normalize("NFC", text)

    # 2. Loại bỏ các ký tự điều khiển/ẩn (Control characters) ngoại trừ \n, \t
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    # 3. Chuẩn hóa khoảng trắng (Xóa khoảng trắng thừa nhưng giữ lại các dòng trống có ý nghĩa)
    # Rút gọn khoảng trắng liên tiếp trên cùng 1 dòng
    text = re.sub(r'[ \t]+', ' ', text)
    # Rút gọn \n liên tiếp thành tối đa 2 \n (tách đoạn)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 4. Strip khoảng trắng ở hai đầu văn bản
    return text.strip()

def clean_ocr_noise(text):
    """
    (Tùy chọn) Hàm sơ chế các lỗi OCR cơ bản bằng Heuristic hoặc Dictionary.
    Có thể mở rộng sau.
    """
    # Xóa các ký tự đặc biệt đứng đơn lẻ do nhiễu hạt trên ảnh scan (ví dụ: | , _ , ^)
    text = re.sub(r'\s+[|_\^]\s+', ' ', text)
    return text