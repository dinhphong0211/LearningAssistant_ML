"""Giao diện tùy chỉnh: phong cách Gen Z rực rỡ, bo góc, gradient.
"""
import json
import html as _html

import streamlit as st
import streamlit.components.v1 as components

# Font Be Vietnam Pro chuẩn tiếng Việt, tròn trịa hiện đại
FONTS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
"""

PALETTES = {
    "dark": {
        "ink": "#09090b", "surface": "#18181b", "surface-raised": "#27272a",
        "rule": "#3f3f46", "amber": "#c084fc", "sage": "#22d3ee", 
        "text": "#fafafa", "muted": "#a1a1aa", "on-accent": "#09090b",
        "gradient": "linear-gradient(135deg, #c084fc 0%, #22d3ee 100%)"
    },
    "light": {
        "ink": "#f4f7fb",             # Nền tổng thể: Xanh xám pastel siêu nhạt
        "surface": "#ffffff",         # Nền các khối (Card, input): Trắng tinh
        "surface-raised": "#eef2f6",  # Nền khi hover
        "rule": "#e2e8f0",            # Viền xám nhạt
        "amber": "#9333ea",           # Tím mộng mơ
        "sage": "#0ea5e9",            # Xanh Sky blue
        "text": "#0f172a",            # Chữ đen xám (dễ đọc, không bị gắt)
        "muted": "#64748b",           # Chữ nhạt
        "on-accent": "#ffffff",
        "gradient": "linear-gradient(135deg, #9333ea 0%, #0ea5e9 100%)"
    },
}

def _vars_css(theme):
    p = PALETTES.get(theme, PALETTES["light"])
    return "\n".join(f"  --{k}: {v};" for k, v in p.items())

def BASE_CSS(theme):
    return f"""
<style>
:root {{
{_vars_css(theme)}
}}

/* 1. CHỈ GÁN FONT CHO CÁC KHỐI CHỨA VĂN BẢN (TRÁNH LÀM HỎNG ICON STREAMLIT) */
html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {{
  font-family: "Be Vietnam Pro", system-ui, sans-serif !important;
}}

h1, h2, h3, .ui-hero-title {{
  font-family: "Be Vietnam Pro", sans-serif !important;
  font-weight: 800 !important;
  letter-spacing: -0.02em;
  color: transparent !important;
  background: var(--gradient);
  -webkit-background-clip: text;
  background-clip: text;
}}

/* 2. NỀN CHÍNH */
[data-testid="stAppViewContainer"], [data-testid="stApp"], [data-testid="stMain"], [data-testid="stHeader"] {{
  background-color: var(--ink) !important; color: var(--text) !important;
}}
[data-testid="stSidebar"] {{
  background-color: var(--surface) !important;
}}
[data-testid="stSidebar"] > div {{
  background-color: transparent !important;
  border-right: 1px solid var(--rule) !important;
}}

/* 3. CARD BÀI HỌC */
[data-testid="stVerticalBlockBorderWrapper"] {{
  border-radius: 20px !important;
  border: 1px solid var(--rule) !important;
  background-color: var(--surface) !important;
  box-shadow: 0 4px 20px rgba(0,0,0, 0.03) !important;
  transition: transform 0.2s;
}}
[data-testid="stVerticalBlockBorderWrapper"]:hover {{
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0,0,0, 0.06) !important;
}}

p, span, label, li, .stMarkdown, [data-testid="stCaptionContainer"] {{ 
  color: var(--text); 
}}

/* =========================================================
   CHIẾN THUẬT BẮN TỈA: GHI ĐÈ NỀN ĐEN MÀ KHÔNG ĐỤNG CHẠM ICON
========================================================= */

/* A. SELECTBOX VÀ INPUT (Sửa chính xác lớp bọc ngoài cùng và nền bên trong) */
div[data-baseweb="select"] > div, 
div[data-baseweb="input"] > div,
.stTextArea textarea {{
  background-color: var(--surface) !important;
  border: 1px solid var(--rule) !important;
  border-radius: 12px !important;
}}
/* Xóa nền đen ẩn bên trong lớp lõi */
div[data-baseweb="select"] > div > div, 
div[data-baseweb="select"] > div > div > div,
div[data-baseweb="input"] > div > input {{
  background-color: transparent !important;
  color: var(--text) !important;
}}
div[data-baseweb="select"] span {{ color: var(--text) !important; }}

/* B. MENU XỔ XUỐNG (Dropdown List) */
ul[role="listbox"], [data-baseweb="menu"], [data-baseweb="popover"] > div {{
  background-color: var(--surface) !important;
  border: 1px solid var(--rule) !important;
  border-radius: 12px !important;
  overflow: hidden;
}}
ul[role="listbox"] li {{
  background-color: transparent !important;
  color: var(--text) !important;
}}
ul[role="listbox"] li:hover {{
  background-color: var(--surface-raised) !important;
  color: var(--sage) !important;
}}

/* C. NÚT POPOVER (KHUNG XÓA) & TOAST THÔNG BÁO */
[data-testid="stPopoverBody"] {{
  background-color: var(--surface) !important;
  border: 1px solid var(--rule) !important;
  border-radius: 16px !important;
  box-shadow: 0 8px 30px rgba(0,0,0, 0.1) !important;
}}
[data-testid="stPopoverBody"] p, [data-testid="stPopoverBody"] span, [data-testid="stPopoverBody"] div {{
  background-color: transparent !important;
  color: var(--text) !important;
}}
[data-testid="stToast"] {{
  background-color: var(--surface) !important;
  border: 2px solid var(--sage) !important;
  border-radius: 12px !important;
  box-shadow: 0 10px 30px rgba(0,0,0, 0.15) !important;
}}
[data-testid="stToast"] p, [data-testid="stToast"] span {{ color: var(--text) !important; }}

/* D. TAG (Thuật ngữ / Model dự phòng) */
span[data-baseweb="tag"] {{
  background-color: color-mix(in srgb, var(--sage) 15%, var(--surface)) !important;
  border-radius: 8px !important;
}}
span[data-baseweb="tag"] span {{ color: var(--sage) !important; }}
span[data-baseweb="tag"] svg {{ fill: var(--sage) !important; }}

/* E. NÚT BẤM CHUNG */
.stButton > button, .stDownloadButton > button, [data-testid="stPopoverBody"] button {{
  background-color: var(--surface) !important;
  color: var(--text) !important;
  border-radius: 16px !important;
  border: 1px solid var(--rule) !important;
  font-family: "Be Vietnam Pro", sans-serif !important;
  font-weight: 700 !important;
  transition: all 0.2s ease !important;
}}
.stButton > button:hover, .stDownloadButton > button:hover, [data-testid="stPopoverBody"] button:hover {{
  border-color: var(--sage) !important;
  background-color: var(--surface-raised) !important;
  transform: translateY(-2px);
  box-shadow: 0 6px 16px color-mix(in srgb, var(--sage) 20%, transparent) !important;
}}
/* Nút Primary Gradient */
button[kind="primary"] {{
  background: var(--gradient) !important;
  border: none !important;
}}
button[kind="primary"] p, button[kind="primary"] div {{
  color: var(--on-accent) !important;
}}
button[kind="primary"]:hover {{
  box-shadow: 0 8px 20px color-mix(in srgb, var(--amber) 40%, transparent) !important;
}}

/* F. DROPZONE TẢI FILE */
[data-testid="stFileUploaderDropzone"] {{
  background-color: var(--surface) !important;
  border: 2px dashed var(--sage) !important;
  border-radius: 20px !important;
}}
[data-testid="stFileUploaderDropzone"]:hover {{ background-color: var(--surface-raised) !important; }}

/* CHECKBOX */
[data-testid="stCheckbox"] div[data-baseweb="checkbox"] > div:first-child {{
  background-color: var(--surface) !important;
  border: 2px solid var(--rule) !important;
}}

/* ========================================================= */

/* Alert box */
[data-testid="stAlert"] {{ 
  background-color: var(--surface) !important; 
  border-radius: 16px !important;
  border-left: 4px solid var(--amber) !important;
}}

/* Thanh Tab Segmented Control */
.ui-tabbar [data-testid="stRadio"] > div[role="radiogroup"] {{
  gap: 8px; flex-wrap: wrap; background-color: var(--surface);
  padding: 6px; border-radius: 20px; border: 1px solid var(--rule);
}}
.ui-tabbar [data-testid="stRadio"] label {{
  padding: 10px 18px !important;
  border-radius: 14px; margin: 0 !important;
  transition: all 0.2s;
}}
.ui-tabbar [data-testid="stRadio"] label:has(input:checked) {{
  background-color: color-mix(in srgb, var(--amber) 12%, var(--surface)) !important;
  font-weight: 700;
}}
.ui-tabbar [data-testid="stRadio"] label:has(input:checked) p {{ color: var(--amber) !important; }}

[data-testid="stMetric"] {{
  background-color: var(--surface) !important;
  border: 1px solid var(--rule) !important;
  border-left: 4px solid var(--sage) !important;
  border-radius: 16px; padding: 14px 18px !important;
  transition: transform 0.2s;
  box-shadow: 0 2px 10px rgba(0,0,0, 0.02);
}}
[data-testid="stMetric"]:hover {{ transform: translateY(-3px); box-shadow: 0 6px 16px rgba(0,0,0, 0.06); }}

/* Bảng */
[data-testid="stTable"] table {{ background-color: var(--surface) !important; border-radius: 12px; overflow: hidden; }}
[data-testid="stTable"] th {{ background-color: var(--surface-raised) !important; color: var(--text) !important; font-weight: 700; }}
[data-testid="stTable"] td {{ color: var(--text) !important; border-color: var(--rule) !important; }}

.ui-hero {{
  padding: 24px 0 20px 0;
  margin-bottom: 16px;
  animation: ui-fade-in .6s cubic-bezier(0.2, 0.8, 0.2, 1);
  text-align: center;
}}
.ui-hero-title {{ font-size: 3rem; margin: 0 0 8px 0; }}
.ui-hero-sub {{ color: var(--muted) !important; font-size: 1.1rem; margin: 0; }}

.ui-chip-row {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 8px; }}
.ui-chip {{
  display: inline-block; padding: 6px 16px; border-radius: 999px;
  background-color: color-mix(in srgb, var(--sage) 12%, var(--surface));
  color: var(--sage) !important;
  border: 1px solid color-mix(in srgb, var(--sage) 30%, transparent);
  font-size: 0.9rem; font-weight: 600; font-family: "Be Vietnam Pro", sans-serif;
  transition: all .2s ease;
}}
.ui-chip:hover {{ 
  transform: translateY(-2px) rotate(2deg); 
  background-color: var(--sage); color: var(--on-accent) !important;
}}

.ui-stepper {{ display: flex; align-items: center; margin: 4px 0 24px 0; }}
.ui-step {{ display: flex; align-items: center; flex: 1; }}
.ui-step:last-child {{ flex: 0; }}
.ui-step-dot {{
  width: 28px; height: 28px; border-radius: 50%;
  border: 2px solid var(--rule); color: var(--muted);
  display: flex; align-items: center; justify-content: center;
  font-size: 0.8rem; font-weight: 800; flex-shrink: 0; background-color: var(--surface);
  transition: all 0.3s;
}}
.ui-step-label {{ font-size: 0.85rem; font-family: "Be Vietnam Pro", sans-serif; color: var(--muted) !important; margin-left: 10px; white-space: nowrap; font-weight: 600; }}
.ui-step-line {{ flex: 1; height: 3px; background-color: var(--rule); margin: 0 12px; border-radius: 2px; }}
.ui-step.done .ui-step-dot {{ background-color: var(--sage); border-color: var(--sage); color: var(--on-accent); }}
.ui-step.done .ui-step-label {{ color: var(--text) !important; }}
.ui-step.active .ui-step-dot {{
  background-color: var(--amber); border-color: var(--amber); color: var(--on-accent);
  box-shadow: 0 0 0 6px color-mix(in srgb, var(--amber) 20%, transparent);
  animation: ui-pulse 1.5s ease-in-out infinite;
}}
.ui-step.active .ui-step-label {{ color: var(--text) !important; font-weight: 800; }}

.ui-eq {{ display: inline-flex; align-items: flex-end; gap: 4px; height: 20px; margin-right: 10px; }}
.ui-eq span {{ width: 4px; background-color: var(--amber); border-radius: 3px; height: 6px; }}
.ui-eq.playing span {{ background: var(--gradient); animation: ui-eq-bounce 0.8s ease-in-out infinite alternate; }}
.ui-eq.playing span:nth-child(2) {{ animation-delay: .1s; }}
.ui-eq.playing span:nth-child(3) {{ animation-delay: .2s; }}
.ui-eq.playing span:nth-child(4) {{ animation-delay: .3s; }}

@keyframes ui-eq-bounce {{ 0% {{ height: 6px; }} 100% {{ height: 20px; }} }}
@keyframes ui-pulse {{ 0%,100% {{ box-shadow: 0 0 0 6px color-mix(in srgb, var(--amber) 20%, transparent); transform: scale(1); }} 50% {{ box-shadow: 0 0 0 10px color-mix(in srgb, var(--amber) 10%, transparent); transform: scale(1.05); }} }}
@keyframes ui-fade-in {{ from {{ opacity: 0; transform: translateY(10px) scale(0.98); }} to {{ opacity: 1; transform: translateY(0) scale(1); }} }}

@media (prefers-reduced-motion: reduce) {{
  .ui-step.active .ui-step-dot, .ui-eq.playing span, .ui-hero, .stButton > button {{ animation: none !important; transition: none !important; transform: none !important; }}
}}
@media (max-width: 640px) {{
  .ui-step-label {{ display: none; }}
  .ui-hero-title {{ font-size: 2.2rem; }}
}}
</style>
"""

MOBILE_CSS = """
<style>
/* ===== Bố cục ưu tiên điện thoại ===== */
.block-container { padding: 1.5rem 1rem 5rem 1rem !important; max-width: 800px !important; }
.ui-hero { padding: 16px 0 16px 0 !important; margin-bottom: 20px !important; }

/* Menu st.segmented_control */
.st-key-nav [data-baseweb="button-group"], .st-key-nav [role="radiogroup"] {
  display: flex; width: 100%; gap: 6px; flex-wrap: nowrap;
  background-color: var(--surface); border: 1px solid var(--rule);
  border-radius: 24px; padding: 6px;
  box-shadow: 0 2px 10px rgba(0,0,0, 0.02);
}
.st-key-nav button {
  flex: 1 1 0; min-height: 50px; border-radius: 18px !important;
  border: none !important; background-color: transparent !important; box-shadow: none !important;
}
.st-key-nav button * { color: var(--muted) !important; font-weight: 700; font-family: "Be Vietnam Pro", sans-serif; }
.st-key-nav button[kind="segmented_controlActive"],
.st-key-nav button[aria-checked="true"] {
  background-color: color-mix(in srgb, var(--amber) 12%, var(--surface)) !important;
}
.st-key-nav button[kind="segmented_controlActive"] p,
.st-key-nav button[aria-checked="true"] p {
  color: var(--amber) !important; font-weight: 800;
}

/* Thẻ bài học */
[class*="st-key-card-"] [data-testid="stHorizontalBlock"] { flex-direction: row !important; flex-wrap: nowrap !important; gap: 10px; }
[class*="st-key-card-"] [data-testid="stColumn"] { min-width: 0 !important; }

/* Nút to trên điện thoại */
.stButton > button, .stDownloadButton > button { min-height: 52px; width: 100%; font-size: 1.05rem !important; }
.stSelectbox [data-baseweb="select"] > div { min-height: 52px; }

/* Tab con */
[data-baseweb="tab-list"] { gap: 6px; overflow-x: auto; padding-bottom: 4px; }
button[data-baseweb="tab"] { min-height: 50px; padding: 0 16px; border-radius: 12px; }
button[data-baseweb="tab"] * { color: var(--muted) !important; font-weight: 700; font-family: "Be Vietnam Pro", sans-serif; }
button[data-baseweb="tab"][aria-selected="true"] { background-color: var(--surface-raised); }
button[data-baseweb="tab"][aria-selected="true"] p { color: var(--amber) !important; }
[data-baseweb="tab-highlight"] { display: none; }

/* Lưới thống kê */
.ui-stats { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin: 16px 0 20px 0; }
@media (min-width: 700px) { .ui-stats { grid-template-columns: repeat(4, 1fr); } }
.ui-stat {
  background-color: var(--surface); border: 1px solid var(--rule);
  border-left: 4px solid var(--sage); border-radius: 16px; padding: 14px 16px; min-width: 0;
  transition: transform 0.2s;
  box-shadow: 0 2px 8px rgba(0,0,0, 0.02);
}
.ui-stat:hover { transform: translateY(-3px); box-shadow: 0 6px 16px rgba(0,0,0, 0.05); }
.ui-stat-label { font-size: .75rem; letter-spacing: .08em; font-family: "Be Vietnam Pro", sans-serif; text-transform: uppercase; font-weight: 700; color: var(--muted) !important; }
.ui-stat-value { font-size: 1.35rem; font-weight: 800; font-family: "Be Vietnam Pro", sans-serif; margin-top: 4px; overflow-wrap: anywhere; }

/* Khối đọc tóm tắt */
.st-key-reading {
  background-color: var(--surface); border: 1px solid var(--rule);
  border-radius: 24px; padding: 24px 26px;
  box-shadow: 0 4px 20px rgba(0,0,0, 0.02);
}
.st-key-reading p, .st-key-reading li { font-size: 1.1rem; line-height: 1.85; }
.st-key-reading li { margin-bottom: .5em; }
.st-key-reading h1, .st-key-reading h2, .st-key-reading h3 { 
  font-size: 1.35rem !important; margin-top: 1.2em; 
  color: transparent !important; background: var(--gradient); -webkit-background-clip: text;
}

/* Thẻ bài học trong Thư viện */
.ui-lesson-title { font-weight: 800; font-family: "Be Vietnam Pro", sans-serif; font-size: 1.15rem; line-height: 1.4; overflow-wrap: anywhere; }
.ui-lesson-meta { color: var(--muted) !important; font-size: .85rem; margin: 4px 0 8px 0; font-weight: 500; }
.ui-lesson-prev { font-size: .95rem; line-height: 1.6; color: var(--text) !important; opacity: .85; }
.ui-badge {
  display: inline-block; font-size: .75rem; font-weight: 800; padding: 4px 10px; margin-bottom: 8px;
  border-radius: 999px; background: var(--gradient); color: var(--on-accent) !important;
}
@media (max-width: 640px) {
  .ui-hero-sub { display: none; }
  .block-container { padding-left: 1rem !important; padding-right: 1rem !important; }
}
</style>
"""

def inject_css(theme="light"):
    st.markdown(FONTS, unsafe_allow_html=True)
    st.markdown(BASE_CSS(theme), unsafe_allow_html=True)
    st.markdown(MOBILE_CSS, unsafe_allow_html=True)

def theme_toggle_button(location=st.sidebar):
    current = st.session_state.get("theme", "light")
    label = "🌙 Chế độ tối" if current == "light" else "✨ Chế độ sáng"
    if location.button(label, key="ui-theme-toggle"):
        st.session_state["theme"] = "dark" if current == "light" else "light"
        st.rerun()
    return st.session_state.get("theme", "light")

def hero(title, subtitle):
    st.markdown(
        f"""<div class="ui-hero">
            <h1 class="ui-hero-title">{_html.escape(title)}</h1>
            <p class="ui-hero-sub">{_html.escape(subtitle)}</p>
        </div>""",
        unsafe_allow_html=True,
    )

def render_stepper(labels, current_index, placeholder=None):
    parts = ['<div class="ui-stepper">']
    for i, label in enumerate(labels):
        state = "done" if i < current_index else ("active" if i == current_index else "")
        parts.append(f'<div class="ui-step {state}">')
        parts.append(f'<div class="ui-step-dot">{"✨" if state == "done" else i + 1}</div>')
        parts.append(f'<div class="ui-step-label">{_html.escape(label)}</div>')
        if i < len(labels) - 1:
            parts.append('<div class="ui-step-line"></div>')
        parts.append("</div>")
    parts.append("</div>")
    (placeholder or st).markdown("".join(parts), unsafe_allow_html=True)

def chips(items):
    if not items:
        st.caption("Trống.")
        return
    row = "".join(f'<span class="ui-chip">{_html.escape(t)}</span>' for t in items)
    st.markdown(f'<div class="ui-chip-row">{row}</div>', unsafe_allow_html=True)

def equalizer(playing=False, label=""):
    cls = "ui-eq playing" if playing else "ui-eq"
    st.markdown(
        f'<div style="display:flex;align-items:center;">'
        f'<span class="{cls}"><span></span><span></span><span></span><span></span></span>'
        f'<span style="color:var(--muted);font-size:0.9rem;font-weight:600;font-family:\'Be Vietnam Pro\',sans-serif;">{_html.escape(label)}</span></div>',
        unsafe_allow_html=True,
    )

def copy_button(text, label="✨ Copy nội dung"):
    safe_text = json.dumps(text or "")
    components.html(
        f"""
        <button id="ui-copy-btn" style="
            background:linear-gradient(135deg, #9333ea, #0ea5e9);color:#ffffff;border:none;border-radius:20px;
            padding:10px 18px;font-family:'Be Vietnam Pro',sans-serif;font-weight:800;
            font-size:0.9rem;cursor:pointer;transition:transform 0.2s;box-shadow:0 4px 14px rgba(147,51,234,0.3);">
            {_html.escape(label)}
        </button>
        <span id="ui-copy-msg" style="margin-left:12px;color:#0ea5e9;font-size:0.85rem;font-weight:700;font-family:'Be Vietnam Pro',sans-serif;"></span>
        <script>
          const btn = document.getElementById("ui-copy-btn");
          const msg = document.getElementById("ui-copy-msg");
          btn.addEventListener("mouseover", () => btn.style.transform = "translateY(-3px) scale(1.02)");
          btn.addEventListener("mouseout", () => btn.style.transform = "translateY(0) scale(1)");
          btn.addEventListener("click", async () => {{
            try {{
              await navigator.clipboard.writeText({safe_text});
              msg.textContent = "Đã copy! 🎉";
              setTimeout(() => msg.textContent = "", 2000);
            }} catch (e) {{
              msg.textContent = "Trình duyệt chặn copy. 🥲";
            }}
          }});
        </script>
        """,
        height=50,
    )

def reading_time_minutes(text, wpm=200):
    words = len((text or "").split())
    return max(1, round(words / wpm))

TAB_OPTIONS = ["📝 Tóm tắt", "📌 Thuật ngữ", "🎧 Audio", "📊 Đánh giá"]

def tabbar():
    st.markdown('<div class="ui-tabbar">', unsafe_allow_html=True)
    choice = st.radio(
        "Khu vực kết quả", TAB_OPTIONS,
        horizontal=True, label_visibility="collapsed", key="active_tab",
    )
    st.markdown("</div>", unsafe_allow_html=True)
    return choice

def stat_grid(items):
    cells = "".join(
        f'<div class="ui-stat"><div class="ui-stat-label">{_html.escape(str(label))}</div>'
        f'<div class="ui-stat-value">{_html.escape(str(value))}</div></div>'
        for label, value in items
    )
    st.markdown(f'<div class="ui-stats">{cells}</div>', unsafe_allow_html=True)

def lesson_card_html(title, meta, preview="", badge=""):
    parts = []
    if badge:
        parts.append(f'<span class="ui-badge">{_html.escape(badge)}</span>')
    parts.append(f'<div class="ui-lesson-title">{_html.escape(title)}</div>')
    parts.append(f'<div class="ui-lesson-meta">{_html.escape(meta)}</div>')
    if preview:
        parts.append(f'<div class="ui-lesson-prev">{_html.escape(preview)}</div>')
    return "".join(parts)