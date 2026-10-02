import os
import time
import uuid
import asyncio
import tempfile

import streamlit as st

from summarization.abstractive import TransformerSummarizer, list_gemini_models
from pipeline import run_pipeline, QUICK_LABEL
from document.loader import SUPPORTED_EXTENSIONS, DocumentError, get_extension
from evaluation.metrics import (
    rouge_all,
    terminology_preservation_rate,
    number_preservation_rate,
    compression_ratio,
)
from utils.export import summary_to_txt_bytes, summary_to_docx_bytes
from tts.speech import normalize_text_for_speech, generate_speech_async

MAX_FILE_MB = 20
VOICES = {
    "Hoài My (nữ)": "vi-VN-HoaiMyNeural",
    "Nam Minh (nam)": "vi-VN-NamMinhNeural",
}
RATES = {
    "Chậm (-20%)": "-20%",
    "Bình thường": "+0%",
    "Nhanh (+10%)": "+10%",
    "Rất nhanh (+25%)": "+25%",
}
GEMINI_ERROR_PREFIX = "Lỗi khi gọi API Gemini"

# --- 1. CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="AI Learning Assistant", page_icon="🎓", layout="wide")
st.title("🎓 Trợ Lý Học Tập Thông Minh")
st.markdown("Hỗ trợ sinh viên đọc, tóm tắt và nghe tài liệu chuyên ngành.")


# --- 2. HÀM CACHE ---
@st.cache_data(ttl=3600)
def get_models():
    return list_gemini_models()


@st.cache_resource
def get_summarizer(model_name):
    return TransformerSummarizer(model_name)


# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("Cài đặt AI")
    try:
        models = get_models()
    except Exception as e:
        st.error(f"Không lấy được danh sách model: {e}")
        st.stop()

    default_idx = next((i for i, m in enumerate(models) if "flash" in m), 0)
    chosen_model = st.selectbox("Model tóm tắt", models, index=default_idx)

    st.header("Giọng đọc")
    voice_label = st.selectbox("Giọng", list(VOICES.keys()))
    rate_label = st.selectbox("Tốc độ", list(RATES.keys()), index=1)

    st.caption(
        "Định dạng hỗ trợ: " + ", ".join(e.lstrip(".").upper() for e in SUPPORTED_EXTENSIONS)
        + f". Tối đa {MAX_FILE_MB} MB."
    )

# --- 4. KHU VỰC TẢI FILE ---
uploaded_file = st.file_uploader(
    "Tải lên tài liệu học tập",
    type=[e.lstrip(".") for e in SUPPORTED_EXTENSIONS],
)

summary_mode = st.radio(
    "Lựa chọn mức độ tóm tắt:",
    (QUICK_LABEL, "Chi tiết bài học (Study Notes - Hỗ trợ nghe)"),
    help="Chọn 'Chi tiết' nếu bạn muốn AI giữ lại nhiều kiến thức để nghe qua Audio.",
)


# --- 5. XỬ LÝ KHI BẤM NÚT ---
def analyze(file, model_name, mode):
    size_mb = file.size / (1024 * 1024)
    if size_mb > MAX_FILE_MB:
        st.error(f"File {size_mb:.1f} MB vượt giới hạn {MAX_FILE_MB} MB.")
        return

    ext = get_extension(file.name)
    if ext not in SUPPORTED_EXTENSIONS:
        st.error(f"Định dạng '{ext}' chưa được hỗ trợ.")
        return

    # Tên file tạm do hệ thống đặt, chỉ giữ phần đuôi đã kiểm tra (chống path traversal)
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(file.getvalue())
        tmp_path = tmp.name

    try:
        summarizer = get_summarizer(model_name)
        bar = st.progress(0.0)
        with st.status("Đang phân tích tài liệu...", expanded=True) as status:

            def on_progress(i, total, label):
                bar.progress(i / total)
                st.write(f"({i + 1}/{total}) {label}...")

            result = run_pipeline(tmp_path, summarizer, mode, progress=on_progress)
            bar.progress(1.0)
            status.update(label="Phân tích hoàn tất!", state="complete", expanded=False)

        result["file_name"] = file.name
        st.session_state["result"] = result

    except DocumentError as e:
        st.error(f"⚠️ {e}")
    except Exception as e:
        st.error(f"Lỗi hệ thống: {e}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


if uploaded_file is not None:
    if st.button("🚀 Bắt đầu phân tích"):
        analyze(uploaded_file, chosen_model, summary_mode)

# --- 6. HIỂN THỊ KẾT QUẢ ---
result = st.session_state.get("result")
if result:
    if result["summary"].startswith(GEMINI_ERROR_PREFIX):
        st.error(result["summary"])
        st.info("Thử chọn model khác ở thanh bên (ví dụ bản flash-lite) hoặc đợi một lúc rồi chạy lại.")
        st.stop()

    for w in result["warnings"]:
        st.warning(w)

    info = result["info"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Loại file", info["type"])
    c2.metric("Số trang/slide", info["pages"] if info["pages"] else "—")
    c3.metric("Số ký tự", f"{info['chars']:,}")
    c4.metric("Số đoạn chia", info["chunks"])

    tab_sum, tab_terms, tab_audio, tab_eval = st.tabs(
        ["📝 Tóm tắt", "📌 Thuật ngữ", "🎧 Audio", "📊 Đánh giá"]
    )

    # ----- Tab tóm tắt -----
    with tab_sum:
        st.info(f"**Lĩnh vực:** {result['domain']} ({result['conf']}%)")
        st.write(result["summary"])

        title = f"Tóm tắt - {result.get('file_name', 'tài liệu')}"
        d1, d2, _ = st.columns([1, 1, 3])
        d1.download_button(
            "⬇️ Tải .txt",
            data=summary_to_txt_bytes(title, result["summary"], result["terms"]),
            file_name="tom_tat.txt",
            mime="text/plain",
        )
        d2.download_button(
            "⬇️ Tải .docx",
            data=summary_to_docx_bytes(title, result["summary"], result["domain"], result["terms"]),
            file_name="tom_tat.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    # ----- Tab thuật ngữ -----
    with tab_terms:
        st.write(
            f"Sau khi lọc và gộp biến thể: **{len(result['terms'])}** thuật ngữ "
            f"(trước khi lọc: {result['raw_terms_count']})."
        )
        st.write(", ".join(result["terms"]) if result["terms"] else "Không có.")
        st.caption("Bộ lọc dựa trên luật đơn giản nên có thể bỏ sót hoặc giữ nhầm một số từ.")

    # ----- Tab audio -----
    with tab_audio:
        st.caption(f"Giọng: {voice_label} | Tốc độ: {rate_label}")
        if st.button("🎧 Tạo audio" if not result["audio"] else "🔁 Tạo lại audio với cài đặt hiện tại"):
            with st.spinner("Đang tổng hợp giọng nói AI..."):
                t0 = time.time()
                speech_text = normalize_text_for_speech(result["summary"])
                path = f"outputs/audio/summary_{uuid.uuid4().hex[:8]}.mp3"
                os.makedirs(os.path.dirname(path), exist_ok=True)
                try:
                    asyncio.run(
                        generate_speech_async(
                            speech_text,
                            path,
                            voice=VOICES[voice_label],
                            rate=RATES[rate_label],
                            max_parallel=8,
                        )
                    )
                    with open(path, "rb") as f:
                        result["audio"] = {
                            "bytes": f.read(),
                            "info": f"Giọng {voice_label}, {rate_label}, "
                                    f"{len(speech_text)} ký tự, {time.time() - t0:.1f}s",
                        }
                except Exception as e:
                    st.error(
                        f"Tạo audio thất bại: {e}. Kiểm tra kết nối mạng "
                        "(Edge TTS cần Internet) rồi thử lại."
                    )

        if result["audio"]:
            st.audio(result["audio"]["bytes"], format="audio/mp3")
            st.download_button(
                "⬇️ Tải audio",
                data=result["audio"]["bytes"],
                file_name="tom_tat.mp3",
                mime="audio/mpeg",
            )
            st.caption(result["audio"]["info"])

    # ----- Tab đánh giá -----
    with tab_eval:
        st.subheader("So sánh baseline và mô hình")
        left, right = st.columns(2)
        with left:
            st.markdown("**Baseline: TextRank (trích xuất, không học máy sinh văn bản)**")
            st.write(result["baseline"])
        with right:
            st.markdown("**Gemini (sinh văn bản, pretrained, chỉ inference)**")
            st.write(result["summary"])

        st.subheader("Độ đo không cần bản tham chiếu")
        rows = []
        for name, text in (("TextRank", result["baseline"]), ("Gemini", result["summary"])):
            tpr = terminology_preservation_rate(text, result["terms"])
            npr = number_preservation_rate(text, result["full_text"])
            cr = compression_ratio(text, result["full_text"])
            rows.append({
                "Phương pháp": name,
                "TPR (giữ thuật ngữ)": f"{tpr['rate']:.0%} ({tpr['kept']}/{tpr['total']})" if tpr else "—",
                "NPR (số có trong gốc)": f"{npr['rate']:.0%}" if npr else "không có số",
                "Số lạ (không có trong gốc)": ", ".join(npr["unsupported"]) if npr and npr["unsupported"] else "—",
                "Tỉ lệ nén": f"{cr:.1%}" if cr else "—",
            })
        st.table(rows)
        st.caption(
            "TPR, NPR, tỉ lệ nén là độ đo do đồ án tự định nghĩa, không phải benchmark chuẩn. "
            "Số lạ chỉ là dấu hiệu nghi ngờ, cần đối chiếu với tài liệu gốc."
        )

        st.subheader("ROUGE (cần bản tóm tắt tham chiếu)")
        reference = st.text_area(
            "Dán bản tóm tắt tham chiếu do người viết (không phải do AI tạo) để tính ROUGE:",
            height=150,
        )
        if reference.strip():
            rouge_rows = []
            for name, text in (("TextRank", result["baseline"]), ("Gemini", result["summary"])):
                r = rouge_all(text, reference)
                rouge_rows.append({
                    "Phương pháp": name,
                    **{k: f"{v['f1']:.3f}" for k, v in r.items()},
                })
            st.table(rouge_rows)
            st.caption(
                "Điểm F1. ROUGE đo độ trùng từ nên có xu hướng thấp với tóm tắt sinh văn bản "
                "(diễn đạt khác tham chiếu) dù nội dung đúng. Một cặp tài liệu chưa đủ để kết luận."
            )
