"""OCR bằng Gemini (multimodal). Không cần cài Tesseract.

Giới hạn cần ghi trong báo cáo:
  - Đây là mô hình ngôn ngữ đọc ảnh, không phải OCR truyền thống: có thể "đọc lại" sai
    hoặc tự sửa chính tả, đặc biệt với công thức, ký hiệu Hy Lạp, chữ nhỏ.
  - Mỗi trang là một lần gọi API (tốn thời gian và quota).
  - Nội dung ảnh được gửi lên máy chủ của Google.
"""

OCR_PROMPT = (
    "Hãy chép lại CHÍNH XÁC toàn bộ văn bản trong ảnh, giữ nguyên ngôn ngữ gốc, "
    "thứ tự đọc, số liệu, đơn vị, ký hiệu và công thức. "
    "Không dịch, không tóm tắt, không thêm bình luận. "
    "Nếu có bảng, chép từng hàng, các ô cách nhau bằng dấu ' | '. "
    "Nếu ảnh không có chữ, trả về đúng một dòng: [KHÔNG CÓ VĂN BẢN]"
)


def make_gemini_ocr(model):
    """Trả về hàm ocr(image_bytes, mime_type) -> str dùng model Gemini đã khởi tạo."""

    def ocr(image_bytes, mime_type="image/png"):
        response = model.generate_content(
            [OCR_PROMPT, {"mime_type": mime_type, "data": image_bytes}]
        )
        text = (response.text or "").strip()
        return "" if text == "[KHÔNG CÓ VĂN BẢN]" else text

    return ocr
