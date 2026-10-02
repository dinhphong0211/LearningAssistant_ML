import re

def merge_pdf_blocks(blocks):
    """
    Ghép nối các block văn bản bị đứt gãy từ PDF thành các đoạn văn hoàn chỉnh.
    """
    merged_paragraphs = []
    current_paragraph = ""

    for b in blocks:
        # Lấy text từ block và xóa khoảng trắng thừa ở 2 đầu
        text = b[4].strip()
        if not text:
            continue
        
        # Xóa các ký tự \n thừa bên trong chính block đó (nếu có)
        text = text.replace('\n', ' ')
        # Rút gọn nhiều khoảng trắng thành 1 khoảng trắng
        text = re.sub(r'\s+', ' ', text)

        if current_paragraph:
            # Kiểm tra xem đoạn hiện tại có kết thúc bằng dấu ngắt câu hay không
            # Bỏ qua ngoặc kép hoặc ngoặc đơn đóng ở cuối câu
            clean_current = re.sub(r'[\'")]*$', '', current_paragraph.strip())
            
            if not re.search(r'[.:?!]$', clean_current):
                # Nối tiếp vào đoạn hiện tại vì câu chưa kết thúc
                current_paragraph += " " + text
            else:
                # Câu đã kết thúc, lưu lại đoạn hiện tại và bắt đầu đoạn mới
                merged_paragraphs.append(current_paragraph)
                current_paragraph = text
        else:
            current_paragraph = text

    # Đẩy đoạn cuối cùng vào danh sách
    if current_paragraph:
        merged_paragraphs.append(current_paragraph)
        
    return merged_paragraphs