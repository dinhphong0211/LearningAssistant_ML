import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import google.generativeai as genai

from preprocessing.chunker import chunk_text

load_dotenv()

# Các từ khóa loại khỏi danh sách model (không dùng để tạo văn bản)
_SKIP = ("image", "tts", "live", "audio", "embedding", "vision")


def configure_gemini():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Chưa có API key. Hãy đặt GEMINI_API_KEY trong file .env")
    genai.configure(api_key=api_key)


def list_gemini_models(include_all=False):
    """Danh sách model tạo văn bản.
    Mặc định chỉ giữ nhóm 'flash' (gồm flash-lite) vì các model khác thường có hạn mức
    miễn phí thấp hoặc bằng 0 và hay báo lỗi 429. include_all=True để xem tất cả."""
    configure_gemini()
    names = []
    for m in genai.list_models():
        name = m.name.replace("models/", "")
        if "generateContent" not in m.supported_generation_methods:
            continue
        if any(s in name for s in _SKIP):
            continue
        if not include_all and "flash" not in name:
            continue
        names.append(name)
    return sorted(names, reverse=True)


def is_rate_limit_error(err):
    """Nhận diện lỗi vượt hạn mức (HTTP 429 / ResourceExhausted)."""
    text = f"{type(err).__name__} {err}".lower()
    return any(k in text for k in ("resourceexhausted", "429", "quota", "rate limit", "too many requests"))


class TransformerSummarizer:
    def __init__(self, model_name=None, fallback_models=(), retry_delays=(3, 8, 15)):
        configure_gemini()
        model_name = model_name or os.environ.get("GEMINI_MODEL") or self._pick_default()
        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name)
        self.fallback_models = [m for m in fallback_models if m and m != model_name]
        self.retry_delays = retry_delays
        self.last_used_model = model_name
        self._models = {model_name: self.model}
        print(f"=> Kết nối Gemini thành công! Model: {model_name} | dự phòng: {self.fallback_models}")

    @staticmethod
    def _pick_default():
        flash = list_gemini_models()
        if not flash:
            raise RuntimeError("Không tìm thấy model flash nào khả dụng.")
        return flash[0]

    @staticmethod
    def _clean_for_tts(text):
        text = re.sub(r"[*_#`>]+", "", text)
        text = re.sub(r"^\s*[-•]\s+", "", text, flags=re.M)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _get_model(self, name):
        if name not in self._models:
            self._models[name] = genai.GenerativeModel(name)
        return self._models[name]

    def _generate(self, prompt):
        """Gọi Gemini. Gặp lỗi vượt hạn mức thì chờ rồi thử lại; nếu vẫn lỗi thì chuyển
        sang model dự phòng. Lỗi khác (không phải 429) được ném lên ngay."""
        last_err = None
        for name in [self.model_name] + self.fallback_models:
            model = self._get_model(name)
            for delay in (0,) + tuple(self.retry_delays):
                if delay:
                    time.sleep(delay)
                try:
                    response = model.generate_content(prompt)
                    self.last_used_model = name
                    return self._clean_for_tts(response.text)
                except Exception as e:
                    if not is_rate_limit_error(e):
                        raise
                    last_err = e
            print(f"[AI] Model {name} bị giới hạn lượt gọi, thử model dự phòng (nếu có)...")
        raise last_err

    # ---------- Đường cũ: tài liệu ngắn ----------
    def summarize_long_document(self, text, detail_level="standard"):
        if not text or len(text.strip()) < 50:
            return text

        if detail_level == "quick":
            prompt = f"""Bạn là một giáo sư đại học. Hãy tóm tắt nhanh tài liệu sau đây trong khoảng 3-4 câu ngắn gọn, súc tích. Tuyệt đối không dùng các ký tự định dạng markdown như *, #, _ để máy đọc văn bản (TTS) có thể đọc tự nhiên.

Tài liệu:
{text[:15000]}"""
        else:
            prompt = f"""Bạn là một trợ lý học tập. Hãy đọc tài liệu chuyên ngành sau và tạo ra một bản "Study Notes" chi tiết nhưng dễ hiểu.
- Chia thành các phần rõ ràng (Phần 1, Phần 2...).
- Giải thích từ khóa khó nếu có.
- Hành văn mượt mà, như đang giảng bài.
- Tuyệt đối KHÔNG sử dụng ký tự in đậm, in nghiêng, gạch đầu dòng (*, #, -) để máy đọc TTS không bị vấp.

Tài liệu:
{text[:30000]}"""

        try:
            return self._generate(prompt)
        except Exception as e:
            return f"Lỗi khi gọi API Gemini: {e}"

    # ---------- Map-reduce: tài liệu dài ----------
    def _summarize_chunk(self, chunk, idx, total):
        prompt = f"""Bạn là trợ lý học tập. Đây là phần {idx}/{total} của một tài liệu chuyên ngành.
Hãy tóm tắt phần này thành một đoạn văn liền mạch, khoảng 5-8 câu.
Yêu cầu:
- Giữ nguyên thuật ngữ chuyên ngành, từ viết tắt, tên mô hình, số liệu, đơn vị và công thức.
- Không thêm thông tin không có trong văn bản.
- Không dùng markdown hay gạch đầu dòng.

Văn bản:
{chunk}"""
        return self._generate(prompt)

    def _merge_group(self, group):
        joined = "\n\n".join(group)
        prompt = f"""Hãy hợp nhất các bản tóm tắt phần dưới đây thành một đoạn văn liền mạch, giữ đúng thứ tự nội dung.
Giữ nguyên thuật ngữ, số liệu, đơn vị, công thức. Không thêm thông tin mới. Không dùng markdown.

{joined}"""
        return self._generate(prompt)

    def _reduce(self, partials, detail_level):
        joined = "\n\n".join(partials)
        if detail_level == "quick":
            instruction = (
                "Hãy hợp nhất các bản tóm tắt phần dưới đây thành MỘT bản tóm tắt chung "
                "khoảng 3-4 câu, súc tích. Không dùng ký tự markdown như *, #, _."
            )
        else:
            instruction = (
                'Hãy hợp nhất các bản tóm tắt phần dưới đây thành một bản "Study Notes" '
                "chi tiết nhưng dễ hiểu cho toàn bộ tài liệu.\n"
                "- Chia thành các phần rõ ràng (Phần 1, Phần 2...).\n"
                "- Giải thích từ khóa khó nếu có.\n"
                "- Hành văn mượt mà, như đang giảng bài.\n"
                "- Tuyệt đối KHÔNG dùng ký tự in đậm, in nghiêng, gạch đầu dòng (*, #, -) "
                "để máy đọc TTS không bị vấp."
            )
        prompt = f"""{instruction}
Giữ nguyên thuật ngữ, số liệu, đơn vị, công thức. Không thêm thông tin không có trong các bản tóm tắt.

Các bản tóm tắt phần:
{joined}"""
        return self._generate(prompt)

    def summarize_map_reduce(
        self,
        text,
        detail_level="standard",
        chunk_chars=6000,
        max_workers=2,          # giảm từ 3: gọi song song nhiều làm dễ dính lỗi 429
        max_reduce_chars=20000,
    ):
        """Tóm tắt tài liệu dài: chia đoạn -> tóm tắt từng đoạn -> gộp."""
        if not text or len(text.strip()) < 50:
            return text

        chunks = chunk_text(text, max_chars=chunk_chars)
        print(f"[AI] Tài liệu được chia thành {len(chunks)} đoạn.")

        if len(chunks) <= 1:
            return self.summarize_long_document(text, detail_level)

        try:
            total = len(chunks)
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                partials = list(
                    pool.map(
                        lambda item: self._summarize_chunk(item[1], item[0] + 1, total),
                        enumerate(chunks),
                    )
                )

            while len("\n\n".join(partials)) > max_reduce_chars and len(partials) > 1:
                groups = [partials[i:i + 5] for i in range(0, len(partials), 5)]
                partials = [self._merge_group(g) for g in groups]

            return self._reduce(partials, detail_level)
        except Exception as e:
            return f"Lỗi khi gọi API Gemini: {e}"

    def summarize(self, text, max_length=150, min_length=40):
        return self.summarize_map_reduce(text, "quick")
