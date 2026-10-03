import os
import time
import asyncio
import tempfile
from datetime import datetime
from pathlib import Path

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
from tts.speech import normalize_text_for_speech, generate_speech_async, fetch_voice_options
import ui_theme
import lesson_store
import audio_player

MAX_FILE_MB = 20
RATES = {
    "Chậm (-20%)": "-20%",
    "Bình thường": "+0%",
    "Nhanh (+10%)": "+10%",
    "Rất nhanh (+25%)": "+25%",
}
GEMINI_ERROR_PREFIX = "Lỗi khi gọi API Gemini"
STEP_LABELS = ["Đọc tài liệu", "Chuẩn hóa", "Chuyên ngành", "Baseline", "Gemini"]

NAV_LIB, NAV_NEW, NAV_LESSON = "📚 Thư viện", "➕ Bài mới", "🎧 Bài học"
NAV_OPTIONS = [NAV_LIB, NAV_NEW, NAV_LESSON]

# --- 1. CẤU HÌNH GIAO DIỆN ---
st.set_page_config(
    page_title="AI Learning Assistant",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="collapsed",
)
if "theme" not in st.session_state:
    st.session_state["theme"] = "dark"
ui_theme.inject_css(st.session_state["theme"])
ui_theme.hero("Trợ Lý Học Tập", "Đọc, tóm tắt và nghe tài liệu chuyên ngành — PDF, Word, PowerPoint, văn bản và ảnh.")
lesson_store.init()


# --- 2. HÀM CACHE ---
@st.cache_data(ttl=3600)
def get_models(include_all):
    return list_gemini_models(include_all=include_all)


@st.cache_resource
def get_summarizer(model_name, fallback_models=()):
    return TransformerSummarizer(model_name, fallback_models=fallback_models)


@st.cache_data(ttl=86400)
def get_voices(include_multilingual):
    return fetch_voice_options(include_multilingual)


# --- 3. SIDEBAR (cài đặt) ---
with st.sidebar:
    ui_theme.theme_toggle_button(st.sidebar)
    st.divider()
    st.header("Cài đặt AI")
    show_all = st.checkbox(
        "Hiện cả model Pro và model khác",
        value=False,
        help="Mặc định chỉ hiện nhóm flash vì các model khác thường hết hạn mức miễn phí "
             "và báo lỗi 'quá nhiều request'.",
    )
    models, chosen_model, fallback_models = [], None, []
    try:
        models = get_models(show_all)
    except Exception as e:
        # Không dừng cả app: vẫn mở thư viện và nghe lại bài cũ được khi chưa gọi được Gemini
        st.error(f"Không lấy được danh sách model: {e}")
    if models:
        default_idx = next((i for i, m in enumerate(models) if "flash-lite" in m), 0)
        chosen_model = st.selectbox("Model tóm tắt", models, index=default_idx)

        others = [m for m in models if m != chosen_model]
        fallback_models = st.multiselect(
            "Model dự phòng",
            others,
            default=[m for m in others if "flash" in m][:2],
            help="Khi model chính bị giới hạn lượt gọi (lỗi 429), app tự chờ rồi thử lại, "
                 "nếu vẫn lỗi sẽ chuyển sang các model này theo thứ tự.",
        )
    else:
        st.warning("Chưa có model khả dụng nên chưa tạo được bài mới. Thư viện vẫn dùng bình thường.")

    st.header("Giọng đọc")
    multi = st.checkbox(
        "Thêm giọng đa ngôn ngữ (thử nghiệm)",
        value=False,
        help="Chưa kiểm chứng chất lượng khi đọc tiếng Việt, hãy nghe thử trước khi dùng. "
             "Bảng phiên âm thuật ngữ của app được chỉnh cho giọng tiếng Việt.",
    )
    voices = get_voices(multi)
    voice_label = st.selectbox("Giọng", list(voices.keys()))
    rate_label = st.selectbox("Tốc độ", list(RATES.keys()), index=1)

    st.caption(
        "Định dạng hỗ trợ: " + ", ".join(e.lstrip(".").upper() for e in SUPPORTED_EXTENSIONS)
        + f". Tối đa {MAX_FILE_MB} MB."
    )


# --- 4. TIỆN ÍCH ĐIỀU HƯỚNG ---
def goto(screen):
    """Chuyển màn hình. Phải đổi qua khóa phụ rồi chạy lại, vì không được gán lại
    giá trị của radio sau khi nó đã được vẽ trong cùng lượt chạy."""
    st.session_state["_goto"] = screen
    st.rerun()


def open_lesson(lesson_id):
    lesson_store.touch(lesson_id)
    st.session_state["current_id"] = lesson_id
    goto(NAV_LESSON)


def fmt_date(iso):
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y %H:%M")
    except (TypeError, ValueError):
        return ""


def make_audio(summary):
    """Tạo audio cho bản tóm tắt bằng giọng/tốc độ đang chọn. Trả về (bytes, mô tả)."""
    t0 = time.time()
    speech_text = normalize_text_for_speech(summary)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        path = os.path.join(tmp, "summary.mp3")
        asyncio.run(
            generate_speech_async(
                speech_text, path,
                voice=voices[voice_label], rate=RATES[rate_label], max_parallel=8,
            )
        )
        with open(path, "rb") as f:
            data = f.read()
    info = f"Giọng {voice_label}, {rate_label}, {len(speech_text)} ký tự, {time.time() - t0:.1f}s"
    return data, info


# --- 5. MÀN HÌNH: THƯ VIỆN ---
def screen_library():
    lessons = lesson_store.list_lessons()
    if not lessons:
        st.info("Chưa có bài học nào. Sang **➕ Bài mới** để tóm tắt tài liệu đầu tiên.")
        if st.button("➕ Tạo bài đầu tiên", type="primary", key="lib-empty"):
            goto(NAV_NEW)
        return

    with_audio = sum(1 for x in lessons if x["has_audio"])
    ui_theme.stat_grid([("Bài đã lưu", len(lessons)), ("Có audio", with_audio)])

    for i, item in enumerate(lessons):
        meta = fmt_date(item["created_at"])
        if item["domain"]:
            meta += f" · {item['domain']}"
        meta += " · 🎧 có audio" if item["has_audio"] else " · chưa có audio"
        badge = "Nghe gần đây" if i == 0 and item["last_opened_at"] else ""
        with st.container(border=True, key=f"card-{item['id']}"):
            st.markdown(
                ui_theme.lesson_card_html(item["title"], meta, item["summary_preview"] or "", badge),
                unsafe_allow_html=True,
            )
            col_open, col_del = st.columns([3, 2])
            label = "▶ Nghe tiếp" if item["has_audio"] else "Mở bài"
            if col_open.button(label, key=f"open-{item['id']}", type="primary" if i == 0 else "secondary"):
                open_lesson(item["id"])
            with col_del.popover("🗑️ Xóa"):
                st.write(f"Xóa bài “{item['title']}” khỏi Thư viện?")
                st.caption("Bài và audio sẽ bị xóa vĩnh viễn.")
                if st.button("Xóa vĩnh viễn", key=f"del-{item['id']}", type="primary"):
                    lesson_store.delete(item["id"])
                    if st.session_state.get("current_id") == item["id"]:
                        st.session_state.pop("current_id", None)
                    st.toast("Đã xóa bài học", icon="🗑️")
                    st.rerun()


# --- 6. MÀN HÌNH: BÀI MỚI ---
def analyze(file, model_name, mode, fallbacks=(), auto_audio=True):
    """Phân tích tài liệu, lưu vào thư viện. Trả về id bài học, hoặc None nếu lỗi."""
    size_mb = file.size / (1024 * 1024)
    if size_mb > MAX_FILE_MB:
        st.error(f"File {size_mb:.1f} MB vượt giới hạn {MAX_FILE_MB} MB.")
        return None

    ext = get_extension(file.name)
    if ext not in SUPPORTED_EXTENSIONS:
        st.error(f"Định dạng '{ext}' chưa được hỗ trợ.")
        return None

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(file.getvalue())
        tmp_path = tmp.name

    lesson_id = None
    try:
        summarizer = get_summarizer(model_name, tuple(fallbacks))
        stepper_slot = st.empty()
        ui_theme.render_stepper(STEP_LABELS, -1, stepper_slot)

        def on_progress(i, total, label):
            ui_theme.render_stepper(STEP_LABELS, i, stepper_slot)

        with st.spinner("Đang phân tích tài liệu..."):
            result = run_pipeline(tmp_path, summarizer, mode, progress=on_progress)
        ui_theme.render_stepper(STEP_LABELS, len(STEP_LABELS), stepper_slot)

        result["file_name"] = file.name
        result["model_used"] = summarizer.last_used_model

        if result["summary"].startswith(GEMINI_ERROR_PREFIX):
            st.error(result["summary"])
            st.info("Thử chọn model khác ở menu ☰ (ví dụ bản flash-lite) hoặc đợi một lúc rồi chạy lại.")
            return None

        lesson_id = lesson_store.save_lesson(Path(file.name).stem, result, file_name=file.name)

        if auto_audio:
            eq_slot = st.empty()
            with eq_slot:
                ui_theme.equalizer(playing=True, label="Đang tổng hợp giọng nói AI...")
            try:
                data, info = make_audio(result["summary"])
                lesson_store.set_audio(lesson_id, data, info)
            except Exception as e:
                st.session_state["flash"] = (
                    "warning",
                    f"Đã lưu bài nhưng tạo audio thất bại: {e}. Bạn có thể tạo lại ngay trong màn hình Bài học.",
                )
            finally:
                eq_slot.empty()

    except DocumentError as e:
        st.error(f"⚠️ {e}")
        return None
    except Exception as e:
        st.error(f"Lỗi hệ thống: {e}")
        return None
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    return lesson_id


def screen_new():
    uploaded_file = st.file_uploader(
        "Tải lên tài liệu học tập",
        type=[e.lstrip(".") for e in SUPPORTED_EXTENSIONS],
    )
    summary_mode = st.radio(
        "Mức độ tóm tắt",
        (QUICK_LABEL, "Chi tiết bài học (Study Notes - Hỗ trợ nghe)"),
        help="Chọn 'Chi tiết' nếu bạn muốn AI giữ lại nhiều kiến thức để nghe qua Audio.",
    )
    auto_audio = st.checkbox("Tạo audio ngay sau khi tóm tắt", value=True)
    st.caption("⚙️ Model AI và giọng đọc chỉnh trong menu ☰ ở góc trên bên trái.")

    if st.button(
        "🚀 Bắt đầu phân tích",
        type="primary",
        disabled=uploaded_file is None or chosen_model is None,
    ):
        lesson_id = analyze(uploaded_file, chosen_model, summary_mode, fallback_models, auto_audio)
        if lesson_id:
            st.toast("Đã lưu vào Thư viện!", icon="🎉")
            open_lesson(lesson_id)


# --- 7. MÀN HÌNH: BÀI HỌC ---
def generate_audio_for(lesson_id, summary):
    eq_slot = st.empty()
    with eq_slot:
        ui_theme.equalizer(playing=True, label="Đang tổng hợp giọng nói AI...")
    ok = False
    try:
        data, info = make_audio(summary)
        lesson_store.set_audio(lesson_id, data, info)
        ok = True
    except Exception as e:
        st.error(f"Tạo audio thất bại: {e}. Kiểm tra kết nối mạng rồi thử lại.")
    finally:
        eq_slot.empty()
    if ok:
        st.rerun()


def evaluation_tab(result):
    st.subheader("So sánh baseline và mô hình")
    st.markdown("**Baseline: TextRank (trích xuất, không học máy sinh văn bản)**")
    st.write(result["baseline"])
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
            rouge_rows.append({"Phương pháp": name, **{k: f"{v['f1']:.3f}" for k, v in r.items()}})
        st.table(rouge_rows)
        st.caption(
            "Điểm F1. ROUGE đo độ trùng từ nên có xu hướng thấp với tóm tắt sinh văn bản "
            "dù nội dung đúng. Một cặp tài liệu chưa đủ để kết luận."
        )


def screen_lesson():
    lesson_id = st.session_state.get("current_id")
    lesson = lesson_store.get_lesson(lesson_id) if lesson_id else None
    if lesson is None:
        st.info("Chưa chọn bài học. Mở một bài trong **📚 Thư viện** để đọc và nghe.")
        if st.button("📚 Về Thư viện", key="lesson-empty"):
            goto(NAV_LIB)
        return

    result = lesson["result"]
    flash = st.session_state.pop("flash", None)
    if flash:
        getattr(st, flash[0])(flash[1])

    st.subheader(lesson["title"])

    # Trình phát luôn nằm trên cùng. Đổi tab con bên dưới không chạy lại trang
    # (st.tabs xử lý phía trình duyệt) nên audio không bị ngắt.
    audio_bytes = lesson_store.get_audio(lesson_id) if lesson["has_audio"] else None
    if audio_bytes:
        theme = st.session_state.get("theme", "dark")
        # id có kèm kích thước audio: tạo lại audio (giọng/tốc độ khác) thì vị trí cũ không còn đúng
        audio_player.render(f"{lesson_id}-{len(audio_bytes)}", lesson["title"], audio_bytes, ui_theme.PALETTES[theme])
        if lesson["audio_info"]:
            st.caption(lesson["audio_info"])
        with st.expander("🔁 Tạo lại audio với giọng/tốc độ hiện tại"):
            st.caption(
                f"Giọng: {voice_label} | Tốc độ: {rate_label}. "
                "Audio mới thay thế audio cũ và sẽ nghe lại từ đầu."
            )
            if st.button("Tạo lại audio", key="regen-audio"):
                generate_audio_for(lesson_id, result["summary"])
    else:
        ui_theme.equalizer(playing=False, label="Bài này chưa có audio.")
        st.caption(f"Giọng: {voice_label} | Tốc độ: {rate_label}")
        if st.button("🎧 Tạo audio", type="primary", key="gen-audio"):
            generate_audio_for(lesson_id, result["summary"])

    info = result["info"]
    read_min = ui_theme.reading_time_minutes(result["summary"])
    ui_theme.stat_grid([
        ("Loại file", info["type"]),
        ("Số trang/slide", info["pages"] if info["pages"] else "—"),
        ("Số đoạn chia", info["chunks"]),
        ("Thời gian đọc", f"~{read_min} phút"),
    ])

    tab_sum, tab_terms, tab_eval, tab_manage = st.tabs(
        ["📝 Tóm tắt", "📌 Thuật ngữ", "📊 Đánh giá", "⚙️ Quản lý"]
    )

    with tab_sum:
        for w in result["warnings"]:
            st.warning(w)
        st.caption(f"Lĩnh vực: {result['domain']} ({result['conf']}%)")
        with st.container(key="reading"):
            st.markdown(result["summary"])
        if result.get("model_used"):
            st.caption(f"Model đã dùng: {result['model_used']}")

        title = f"Tóm tắt - {lesson['title']}"
        st.download_button(
            "⬇️ Tải .txt",
            data=summary_to_txt_bytes(title, result["summary"], result["terms"]),
            file_name="tom_tat.txt",
            mime="text/plain",
        )
        st.download_button(
            "⬇️ Tải .docx",
            data=summary_to_docx_bytes(title, result["summary"], result["domain"], result["terms"]),
            file_name="tom_tat.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        ui_theme.copy_button(result["summary"])

    with tab_terms:
        st.write(
            f"Sau khi lọc và gộp biến thể: **{len(result['terms'])}** thuật ngữ "
            f"(trước khi lọc: {result['raw_terms_count']})."
        )
        ui_theme.chips(result["terms"])
        st.caption("Bộ lọc dựa trên luật đơn giản nên có thể bỏ sót hoặc giữ nhầm một số từ.")

    with tab_eval:
        evaluation_tab(result)

    with tab_manage:
        new_title = st.text_input("Tên bài học", value=lesson["title"], key=f"rename-{lesson_id}")
        if st.button("Lưu tên", key="rename-btn") and lesson_store.rename(lesson_id, new_title):
            st.rerun()
        if audio_bytes:
            st.download_button(
                "⬇️ Tải audio (.mp3)", data=audio_bytes, file_name="tom_tat.mp3", mime="audio/mpeg"
            )
        st.divider()
        confirm = st.checkbox("Tôi chắc chắn muốn xóa bài này khỏi Thư viện", key="confirm-del")
        if st.button("🗑️ Xóa bài học", disabled=not confirm, key="delete-btn"):
            lesson_store.delete(lesson_id)
            st.session_state.pop("current_id", None)
            goto(NAV_LIB)


# --- 8. ĐIỀU HƯỚNG ---
if "_goto" in st.session_state:
    st.session_state["nav"] = st.session_state.pop("_goto")
# Bấm lại vào mục đang chọn sẽ bỏ chọn (None): giữ nguyên màn hình hiện tại
if st.session_state.get("nav") not in NAV_OPTIONS:
    st.session_state["nav"] = st.session_state.get("_nav_last", NAV_LIB)

if hasattr(st, "segmented_control"):
    screen = st.segmented_control(
        "Màn hình", NAV_OPTIONS, selection_mode="single",
        label_visibility="collapsed", key="nav",
    )
else:  # Streamlit cũ chưa có segmented_control
    screen = st.radio(
        "Màn hình", NAV_OPTIONS, horizontal=True, label_visibility="collapsed", key="nav",
    )
screen = screen or st.session_state.get("_nav_last", NAV_LIB)
st.session_state["_nav_last"] = screen

if screen == NAV_LIB:
    screen_library()
elif screen == NAV_NEW:
    screen_new()
else:
    screen_lesson()
