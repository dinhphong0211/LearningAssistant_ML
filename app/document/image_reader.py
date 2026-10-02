import pymupdf
import pytesseract
from PIL import Image
import io
import os

# Cấu hình đường dẫn Tesseract trên Windows (Sửa lại nếu đường dẫn cài đặt của bạn khác)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_text_with_ocr(file_path):
    """
    Sử dụng OCR để trích xuất văn bản từ một trang PDF (bằng cách render ra ảnh)
    """
    if not os.path.exists(file_path):
        print(f"Lỗi: Không tìm thấy file tại '{file_path}'")
        return

    try:
        doc = pymupdf.open(file_path)
        page = doc[0] # Test với trang đầu tiên

        # Kiểm tra nhanh xem trang có text layer không
        text_layer = page.get_text()
        if text_layer.strip():
            print("=> Trang này CÓ text layer, không cần OCR (hoặc có thể kết hợp).")
        else:
            print("=> Trang này KHÔNG CÓ text layer, bắt đầu chạy OCR...")

        # 1. Render trang PDF thành hình ảnh (độ phân giải cao: zoom x2)
        zoom = pymupdf.Matrix(2, 2) 
        pix = page.get_pixmap(matrix=zoom)

        # 2. Chuyển Pixmap thành đối tượng hình ảnh của thư viện Pillow
        img = Image.open(io.BytesIO(pix.tobytes()))

        # 3. Chạy Tesseract OCR (chỉ định ngôn ngữ tiếng Việt + tiếng Anh)
        ocr_text = pytesseract.image_to_string(img, lang='vie+eng')

        print("\n--- NỘI DUNG OCR TRÍCH XUẤT ---")
        print(ocr_text)

        doc.close()

    except Exception as e:
        print(f"Lỗi OCR: {e}")

if __name__ == "__main__":
    # Test thử với chính file sample.pdf hiện tại
    sample_path = "../../data/sample.pdf"
    
    # Để test code chuẩn xác từ thư mục gốc, sửa đường dẫn cứng:
    # Lấy đường dẫn gốc của project
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
    test_file = os.path.join(project_root, 'data', 'sample.pdf')
    
    extract_text_with_ocr(test_file)