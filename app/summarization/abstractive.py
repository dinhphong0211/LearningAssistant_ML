import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import google.generativeai as genai

from preprocessing.chunker import chunk_text, chunk_paragraphs

load_dotenv()

GEMINI_ERROR_PREFIX = "Lỗi khi gọi API Gemini"

# --- Chế độ "Đọc toàn bộ": Gemini chép lại nguyên văn, chỉ bỏ nhiễu ---
SKIP_MARK = "[BỎ QUA]"        # Gemini trả về khi cả khối chỉ toàn thứ cần loại bỏ
SKIP_MAX_CHARS = 3000          # khối dài hơn mức này mà bị "bỏ qua" thì không tin, giữ bản gốc
RATIO_MIN_CHARS = 1500         # khối từ mức này trở lên mới kiểm tra tỉ lệ giữ lại nghiêm ngặt

READING_PROMPT = """Bạn đang chuẩn bị văn bản để máy đọc thành tiếng. Đây là phần {idx}/{total} của một tài liệu.
Hãy chép lại TOÀN BỘ nội dung phần này, giữ nguyên từng câu chữ, thứ tự, ngôn ngữ, thuật ngữ, từ viết tắt, số liệu, đơn vị, công thức và các đoạn xuống dòng. TUYỆT ĐỐI KHÔNG tóm tắt, rút gọn, diễn đạt lại, dịch, sửa nội dung hay thêm bình luận.

Chỉ được LOẠI BỎ những thứ không cần thiết khi nghe:
- tên tác giả, người biên soạn, đơn vị công tác, email, số điện thoại, địa chỉ liên hệ của tác giả
- số trang, tiêu đề đầu trang hoặc chân trang lặp lại, mã tài liệu, thông tin bản quyền, ngày phát hành
- mục lục
Không loại bỏ nội dung chính, kể cả khi nó trông giống tiêu đề hoặc tên riêng (ví dụ tên người được nhắc tới trong nội dung bài).
Nếu cả phần này chỉ gồm những thứ cần loại bỏ, trả về đúng một dòng: {skip}

Định dạng: văn xuôi thuần, các đoạn cách nhau bằng một dòng trống, không dùng markdown hay gạch đầu dòng (*, #, -).

Văn bản:
{chunk}"""

# Model dự phòng theo thứ tự ưu tiên: khi model chính bị giới hạn lượt gọi (429) hoặc quá tải
# thì thử lần lượt các model này. Đổi bằng biến môi trường GEMINI_FALLBACK_MODELS
# (các tên cách nhau bởi dấu phẩy), ví dụ: "gemini-3.8-flash,gemini-3.5-flash-lite".
_DEFAULT_FALLBACKS = ("gemini-3.8-flash", "gemini-3.5-flash-lite")


def get_fallback_models():
    raw = os.environ.get("GEMINI_FALLBACK_MODELS", "")
    names = [n.strip().replace("models/", "") for n in raw.split(",") if n.strip()]
    return tuple(dict.fromkeys(names)) or _DEFAULT_FALLBACKS


FALLBACK_MODELS = get_fallback_models()

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


def _err_text(err):
    return f"{type(err).__name__} {err}".lower()


def is_rate_limit_error(err):
    """Nhận diện lỗi vượt hạn mức (HTTP 429 / ResourceExhausted)."""
    return any(k in _err_text(err) for k in ("resourceexhausted", "429", "quota", "rate limit", "too many requests"))


def is_overloaded_error(err):
    """Model đang quá tải / tạm thời không phục vụ (HTTP 503 / 504). Đáng chờ rồi thử lại."""
    return any(k in _err_text(err) for k in (
        "serviceunavailable", "503", "overloaded", "unavailable", "deadlineexceeded", "504",
    ))


def is_model_unavailable_error(err):
    """Model không tồn tại hoặc tài khoản/khóa API không dùng được (HTTP 404).
    Chờ cũng vô ích nên chuyển ngay sang model tiếp theo."""
    text = _err_text(err)
    return "notfound" in text or "404" in text or "is not found" in text or "is not supported for" in text


class TransformerSummarizer:
    def __init__(self, model_name=None, fallback_models=None, retry_delays=(3, 8, 15)):
        configure_gemini()
        # fallback_models=None -> dùng 2 model dự phòng mặc định; truyền () để tắt dự phòng
        if fallback_models is None:
            fallback_models = FALLBACK_MODELS
        model_name = model_name or os.environ.get("GEMINI_MODEL") or self._pick_default(exclude=fallback_models)
        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name)
        self.fallback_models = [m for m in fallback_models if m and m != model_name]
        self.retry_delays = retry_delays
        self.last_used_model = model_name
        self._models = {model_name: self.model}
        print(f"=> Kết nối Gemini thành công! Model: {model_name} | dự phòng: {self.fallback_models}")

    @staticmethod
    def _pick_default(exclude=()):
        flash = [m for m in list_gemini_models() if m not in exclude]
        if not flash:
            raise RuntimeError("Không tìm thấy model flash nào khả dụng.")
        return next((m for m in flash if "flash-lite" in m), flash[0])

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
        """Gọi Gemini theo thứ tự: model chính rồi lần lượt các model dự phòng.

        - Lỗi 429 / quá tải (503): chờ theo retry_delays rồi thử lại; hết lượt thì sang model kế.
        - Model không tồn tại hoặc khóa API không dùng được (404): sang model kế ngay.
        - Lỗi khác (ví dụ API key sai, prompt bị chặn): ném lên ngay vì đổi model cũng không giúp.
        """
        last_err = None
        models = [self.model_name] + self.fallback_models
        for pos, name in enumerate(models):
            model = self._get_model(name)
            reason = None
            for delay in (0,) + tuple(self.retry_delays):
                if delay:
                    time.sleep(delay)
                try:
                    response = model.generate_content(prompt)
                    text = self._clean_for_tts(response.text)
                    if name != self.model_name:
                        print(f"[AI] Đã dùng model dự phòng: {name}")
                    self.last_used_model = name
                    return text
                except Exception as e:
                    if is_model_unavailable_error(e):
                        last_err, reason = e, "không dùng được"
                        break
                    if not (is_rate_limit_error(e) or is_overloaded_error(e)):
                        raise
                    last_err, reason = e, "bị giới hạn lượt gọi hoặc quá tải"
            if pos + 1 < len(models):
                print(f"[AI] Model {name} {reason}, chuyển sang {models[pos + 1]}...")
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
            return f"{GEMINI_ERROR_PREFIX}: {e}"

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
            return f"{GEMINI_ERROR_PREFIX}: {e}"

    # ---------- Đọc toàn bộ: không tóm tắt ----------
    def prepare_reading_text(self, text, chunk_chars=6000, max_workers=2, min_keep_ratio=0.6):
        """Làm sạch toàn văn để đọc, KHÔNG tóm tắt. Trả về (văn_bản, báo_cáo).

        Chia văn bản theo đoạn (không chồng lấn), nhờ Gemini chép lại nguyên văn từng khối và
        chỉ bỏ tác giả/liên hệ/mục lục/số trang. Vì mô hình ngôn ngữ có xu hướng tự rút gọn,
        mỗi khối được kiểm tra; khối nào không đạt thì GIỮ NGUYÊN bản đầu vào:
          - Gemini lỗi (hết hạn mức ở mọi model, bị chặn...) -> "error"
          - kết quả ngắn hơn min_keep_ratio so với đầu vào -> "short" (nghi bị tóm tắt)
          - trả [BỎ QUA] cho khối dài hơn SKIP_MAX_CHARS -> "short"
        Báo cáo: {"chunks", "ai", "dropped", "kept_raw", "errors": [thông báo lỗi]}.
        """
        paragraphs = [p for p in (text or "").split("\n\n") if p.strip()]
        chunks = chunk_paragraphs(paragraphs, max_chars=chunk_chars)
        total = len(chunks)
        print(f"[AI] Đọc toàn bộ: {total} khối.")

        def work(item):
            idx, chunk = item
            prompt = READING_PROMPT.format(idx=idx + 1, total=total, skip=SKIP_MARK, chunk=chunk)
            try:
                out = self._generate(prompt)
            except Exception as e:  # mọi lỗi đều giữ bản gốc của khối, không bỏ mất nội dung
                return chunk, "error", str(e)
            if out.strip() == SKIP_MARK:
                return ("", "dropped", "") if len(chunk) <= SKIP_MAX_CHARS else (chunk, "short", "")
            floor = min_keep_ratio if len(chunk) >= RATIO_MIN_CHARS else 0.3
            if len(out.strip()) < floor * len(chunk):
                return chunk, "short", ""
            return out, "ai", ""

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            results = list(pool.map(work, enumerate(chunks)))

        report = {"chunks": total, "ai": 0, "dropped": 0, "kept_raw": 0, "errors": []}
        for _, status, err in results:
            if status == "ai":
                report["ai"] += 1
            elif status == "dropped":
                report["dropped"] += 1
            else:
                report["kept_raw"] += 1
                if err:
                    report["errors"].append(err)
        merged = "\n\n".join(t.strip() for t, _, _ in results if t.strip())
        return merged, report

    def summarize(self, text, max_length=150, min_length=40):
        return self.summarize_map_reduce(text, "quick")
