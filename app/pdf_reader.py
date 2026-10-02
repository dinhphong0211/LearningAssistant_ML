import pymupdf # Sửa thành import pymupdf nếu bạn đã update theo cảnh báo
import os
from preprocessing.cleaner import merge_pdf_blocks
from preprocessing.text_normalizer import normalize_vietnamese_text # Gọi hàm mới

def read_and_preprocess_pdf(file_path):
    if not os.path.exists(file_path):
        print(f"Lỗi: Không tìm thấy file tại '{file_path}'")
        return

    try:
        # Thay pymupdf bằng pymupdf nếu máy bạn yêu cầu
        doc = pymupdf.open(file_path)
        page = doc[0]
        blocks = page.get_text("blocks")
        
        # 1. Ghép nối đứt gãy
        paragraphs = merge_pdf_blocks(blocks)

        print("\n--- KẾT QUẢ SAU KHI TIỀN XỬ LÝ (PREPROCESSING) ---")
        for i, para in enumerate(paragraphs):
            # 2. Chuẩn hóa Unicode và làm sạch nhiễu cho từng đoạn
            cleaned_para = normalize_vietnamese_text(para)
            print(f"[CLEANED PARA {i}] {cleaned_para}\n")

        doc.close()

    except Exception as e:
        print(f"Lỗi khi xử lý file PDF: {e}")

if __name__ == "__main__":
    sample_pdf_path = "data/sample.pdf"
    read_and_preprocess_pdf(sample_pdf_path)