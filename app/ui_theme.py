"""Giao diện tùy chỉnh: màu sắc, font, và các thành phần HTML nhỏ.

Theme sáng/tối do CHÍNH module này sơn toàn bộ (nền + chữ) cho mọi khối, không
dựa vào config.toml, vì config.toml là cấu hình tĩnh, không đổi được theo lựa
chọn của người dùng lúc app đang chạy. Mọi rule nền/chữ đều có !important vì
Streamlit tự sinh class nội bộ có độ ưu tiên cao hơn CSS thường.
"""
import json
import html as _html

import streamlit as st
import streamlit.components.v1 as components

FONTS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap" rel="stylesheet">
"""

PALETTES = {
    "dark": {
        "ink": "#11151C", "surface": "#1A2130", "surface-raised": "#212A3D",
        "rule": "#2E3850", "amber": "#E3A23D", "sage": "#8BB174",
        "text": "#ECEEF2", "muted": "#96A0B5", "on-accent": "#11151C",
    },
    "light": {
        "ink": "#FAF8F3", "surface": "#FFFFFF", "surface-raised": "#F0EEE6",
        "rule": "#DCD7CA", "amber": "#B5671A", "sage": "#3F7A2D",
        "text": "#1C2230", "muted": "#5B6372", "on-accent": "#FFFFFF",
    },
}


def _vars_css(theme):
    p = PALETTES.get(theme, PALETTES["dark"])
    return "\n".join(f"  --{k}: {v};" for k, v in p.items())


def BASE_CSS(theme):
    return f"""
<style>
:root {{
{_vars_css(theme)}
}}

html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
  font-family: "Be Vietnam Pro", system-ui, sans-serif !important;
}}
h1, h2, h3, .ui-hero-title {{
  font-family: "Fraunces", Georgia, serif !important;
  font-weight: 700 !important;
  letter-spacing: -0.01em;
  color: var(--text) !important;
}}

/* --- Khối lớn: nền + chữ --- */
[data-testid="stAppViewContainer"], [data-testid="stApp"], [data-testid="stMain"] {{
  background: var(--ink) !important; color: var(--text) !important;
}}
[data-testid="stSidebar"], [data-testid="stSidebar"] > div {{
  background: var(--surface) !important;
  border-right: 1px solid var(--rule) !important;
}}
[data-testid="stHeader"] {{ background: var(--ink) !important; }}
[data-testid="stToolbar"] {{ color: var(--text) !important; }}

/* Chữ thường: markdown, nhãn, caption */
p, span, label, li, .stMarkdown, [data-testid="stCaptionContainer"],
[data-testid="stMarkdownContainer"] {{ color: var(--text) !important; }}
[data-testid="stCaptionContainer"] * {{ color: var(--muted) !important; }}

/* --- Nút bấm: tự sơn cả nền lẫn chữ, không phụ thuộc config.toml --- */
.stButton > button, .stDownloadButton > button {{
  background: var(--surface) !important;
  color: var(--text) !important;
  border-radius: 8px !important;
  border: 1px solid var(--rule) !important;
  font-weight: 600 !important;
  transition: transform .1s ease, border-color .15s ease;
}}
.stButton > button *, .stDownloadButton > button * {{ color: var(--text) !important; }}
.stButton > button:hover, .stDownloadButton > button:hover {{
  border-color: var(--sage) !important;
  transform: translateY(-1px);
}}
.stButton > button:active, .stDownloadButton > button:active {{ transform: translateY(0); }}

/* Nút chính (type="primary"): nền màu nhấn, chữ tương phản */
button[kind="primary"], button[kind="primaryFormSubmit"] {{
  background: var(--sage) !important;
  color: var(--on-accent) !important;
  border: none !important;
}}
button[kind="primary"] * {{ color: var(--on-accent) !important; }}

/* Ô chọn (selectbox), vùng nhập, khung tải file */
[data-baseweb="select"] > div, [data-baseweb="input"] > div, textarea,
[data-testid="stFileUploaderFile"] {{
  background: var(--surface) !important;
  color: var(--text) !important;
  border-color: var(--rule) !important;
}}
[data-testid="stFileUploaderFile"] * {{ color: var(--text) !important; }}
[data-testid="stFileUploaderDropzone"] {{
  background: var(--surface) !important;
  border: 1.5px dashed var(--rule) !important;
  border-radius: 10px !important;
  color: var(--text) !important;
  transition: border-color .15s ease, background .15s ease;
}}
[data-testid="stFileUploaderDropzone"] * {{ color: var(--text) !important; }}
[data-testid="stFileUploaderDropzone"]:hover {{
  border-color: var(--amber) !important;
  background: var(--surface-raised) !important;
}}

/* Khung cảnh báo info/warning/error/success */
[data-testid="stAlert"] {{ background: var(--surface) !important; }}
[data-testid="stAlert"] p, [data-testid="stAlert"] span {{ color: var(--text) !important; }}

/* Thanh "tab" tự làm bằng st.radio ngang */
.ui-tabbar [data-testid="stRadio"] > div[role="radiogroup"] {{
  border-bottom: 1px solid var(--rule); gap: 2px; flex-wrap: wrap;
}}
.ui-tabbar [data-testid="stRadio"] label {{
  padding: 8px 14px 10px 14px !important;
  border-radius: 8px 8px 0 0;
  margin-right: 2px !important;
}}
.ui-tabbar [data-testid="stRadio"] label:has(input:checked) {{
  background: var(--surface-raised) !important;
  box-shadow: inset 0 -2px 0 var(--amber);
  font-weight: 600;
}}

[data-testid="stProgress"] > div > div > div {{ background: var(--amber) !important; }}

[data-testid="stMetric"] {{
  background: var(--surface) !important;
  border: 1px solid var(--rule) !important;
  border-left: 3px solid var(--sage) !important;
  border-radius: 6px;
  padding: 10px 14px !important;
}}
[data-testid="stMetricLabel"] *, [data-testid="stMetricValue"] * {{ color: var(--text) !important; }}

/* Bảng (st.table) */
[data-testid="stTable"] {{ color: var(--text) !important; }}
[data-testid="stTable"] table {{ background: var(--surface) !important; }}
[data-testid="stTable"] th {{ background: var(--surface-raised) !important; color: var(--text) !important; }}
[data-testid="stTable"] td {{ color: var(--text) !important; border-color: var(--rule) !important; }}

.ui-hero {{
  padding: 28px 0 20px 0;
  border-bottom: 1px solid var(--rule);
  margin-bottom: 22px;
  animation: ui-fade-in .5s ease;
}}
.ui-hero-title {{ font-size: 2.1rem; margin: 0 0 6px 0; }}
.ui-hero-sub {{ color: var(--muted) !important; font-size: 1rem; margin: 0; }}

.ui-chip-row {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 6px; }}
.ui-chip {{
  display: inline-block; padding: 5px 12px; border-radius: 999px;
  background: color-mix(in srgb, var(--sage) 16%, var(--surface));
  color: var(--sage) !important;
  border: 1px solid color-mix(in srgb, var(--sage) 40%, transparent);
  font-size: 0.85rem; font-weight: 500;
  transition: transform .1s ease;
}}
.ui-chip:hover {{ transform: translateY(-1px); }}

.ui-stepper {{ display: flex; align-items: center; margin: 4px 0 18px 0; }}
.ui-step {{ display: flex; align-items: center; flex: 1; }}
.ui-step:last-child {{ flex: 0; }}
.ui-step-dot {{
  width: 22px; height: 22px; border-radius: 50%;
  border: 2px solid var(--rule); color: var(--muted);
  display: flex; align-items: center; justify-content: center;
  font-size: 0.7rem; font-weight: 700; flex-shrink: 0; background: var(--ink);
}}
.ui-step-label {{ font-size: 0.78rem; color: var(--muted) !important; margin-left: 8px; white-space: nowrap; }}
.ui-step-line {{ flex: 1; height: 2px; background: var(--rule); margin: 0 10px; }}
.ui-step.done .ui-step-dot {{ background: var(--sage); border-color: var(--sage); color: var(--on-accent); }}
.ui-step.done .ui-step-label {{ color: var(--text) !important; }}
.ui-step.active .ui-step-dot {{
  background: var(--amber); border-color: var(--amber); color: var(--on-accent);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--amber) 25%, transparent);
  animation: ui-pulse 1.2s ease-in-out infinite;
}}
.ui-step.active .ui-step-label {{ color: var(--text) !important; font-weight: 600; }}

.ui-eq {{ display: inline-flex; align-items: flex-end; gap: 3px; height: 16px; margin-right: 8px; }}
.ui-eq span {{ width: 3px; background: var(--amber); border-radius: 2px; height: 4px; }}
.ui-eq.playing span {{ animation: ui-eq-bounce 0.9s ease-in-out infinite; }}
.ui-eq.playing span:nth-child(2) {{ animation-delay: .15s; }}
.ui-eq.playing span:nth-child(3) {{ animation-delay: .3s; }}
.ui-eq.playing span:nth-child(4) {{ animation-delay: .45s; }}

@keyframes ui-eq-bounce {{ 0%,100% {{ height: 4px; }} 50% {{ height: 16px; }} }}
@keyframes ui-pulse {{ 0%,100% {{ box-shadow: 0 0 0 4px color-mix(in srgb, var(--amber) 25%, transparent); }} 50% {{ box-shadow: 0 0 0 7px color-mix(in srgb, var(--amber) 12%, transparent); }} }}
@keyframes ui-fade-in {{ from {{ opacity: 0; transform: translateY(4px); }} to {{ opacity: 1; transform: translateY(0); }} }}

@media (prefers-reduced-motion: reduce) {{
  .ui-step.active .ui-step-dot, .ui-eq.playing span, .ui-hero {{ animation: none !important; }}
}}
@media (max-width: 640px) {{
  .ui-step-label {{ display: none; }}
  .ui-hero-title {{ font-size: 1.6rem; }}
}}
</style>
"""


MOBILE_CSS = """
<style>
/* ===== Bố cục ưu tiên điện thoại ===== */
.block-container { padding: 1rem 1rem 4rem 1rem !important; max-width: 760px !important; }
.ui-hero { padding: 14px 0 12px 0 !important; margin-bottom: 14px !important; }
.ui-hero-title { font-size: 1.7rem !important; }

/* Thanh điều hướng 3 màn hình (st.segmented_control: nút liền nhau, không có vòng tròn radio) */
.st-key-nav [data-baseweb="button-group"], .st-key-nav [role="radiogroup"] {
  display: flex; width: 100%; gap: 4px; flex-wrap: nowrap;
  background: var(--surface); border: 1px solid var(--rule);
  border-radius: 14px; padding: 4px;
}
.st-key-nav button {
  flex: 1 1 0; min-height: 46px; border-radius: 10px !important;
  border: none !important; background: transparent !important; box-shadow: none !important;
}
.st-key-nav button * { color: var(--text) !important; font-weight: 600; }
.st-key-nav button[kind="segmented_controlActive"],
.st-key-nav button[aria-checked="true"], .st-key-nav button[aria-pressed="true"] {
  background: var(--sage) !important;
}
.st-key-nav button[kind="segmented_controlActive"] *,
.st-key-nav button[aria-checked="true"] *, .st-key-nav button[aria-pressed="true"] * {
  color: var(--on-accent) !important; font-weight: 700;
}
/* Phương án dự phòng khi Streamlit cũ dùng st.radio */
.st-key-nav label { flex: 1 1 0; justify-content: center; text-align: center; margin: 0 !important; border-radius: 10px; }
.st-key-nav label > div:not([data-testid="stMarkdownContainer"]) { display: none !important; }
.st-key-nav label:has(input:checked) { background: var(--sage) !important; }
.st-key-nav label:has(input:checked) * { color: var(--on-accent) !important; font-weight: 700; }

/* Thẻ bài học: giữ nút Nghe tiếp / Xóa nằm cùng một hàng cả trên điện thoại */
[class*="st-key-card-"] [data-testid="stHorizontalBlock"] { flex-direction: row !important; flex-wrap: nowrap !important; gap: 8px; }
[class*="st-key-card-"] [data-testid="stColumn"] { min-width: 0 !important; }

/* Nút to, dễ bấm bằng ngón tay */
.stButton > button, .stDownloadButton > button { min-height: 48px; width: 100%; }
[data-baseweb="select"] > div { min-height: 48px; }

/* Tab con trong màn hình Bài học */
[data-baseweb="tab-list"] { gap: 4px; overflow-x: auto; }
button[data-baseweb="tab"] { min-height: 46px; padding: 0 14px; }
button[data-baseweb="tab"] * { color: var(--muted) !important; font-weight: 600; }
button[data-baseweb="tab"][aria-selected="true"] * { color: var(--text) !important; }
[data-baseweb="tab-highlight"] { background-color: var(--amber) !important; }

/* Lưới thống kê: 2 cột trên điện thoại, 4 cột trên màn hình rộng */
.ui-stats { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin: 12px 0 16px 0; }
@media (min-width: 700px) { .ui-stats { grid-template-columns: repeat(4, 1fr); } }
.ui-stat {
  background: var(--surface); border: 1px solid var(--rule);
  border-left: 3px solid var(--sage); border-radius: 10px; padding: 10px 12px; min-width: 0;
}
.ui-stat-label { font-size: .7rem; letter-spacing: .05em; text-transform: uppercase; color: var(--muted) !important; }
.ui-stat-value { font-size: 1.2rem; font-weight: 700; margin-top: 2px; overflow-wrap: anywhere; }

/* Khối đọc tóm tắt: chữ lớn, dòng thoáng, hợp đọc trên màn hình nhỏ */
.st-key-reading {
  background: var(--surface); border: 1px solid var(--rule);
  border-radius: 14px; padding: 16px 18px;
}
.st-key-reading p, .st-key-reading li { font-size: 1.06rem; line-height: 1.8; }
.st-key-reading li { margin-bottom: .35em; }
.st-key-reading h1, .st-key-reading h2, .st-key-reading h3 { font-size: 1.2rem !important; margin-top: 1.1em; }

/* Thẻ bài học trong Thư viện */
.ui-lesson-title { font-weight: 700; font-size: 1.05rem; line-height: 1.35; overflow-wrap: anywhere; }
.ui-lesson-meta { color: var(--muted) !important; font-size: .8rem; margin: 2px 0 6px 0; }
.ui-lesson-prev { font-size: .9rem; line-height: 1.5; color: var(--text) !important; opacity: .85; }
.ui-badge {
  display: inline-block; font-size: .7rem; font-weight: 700; padding: 2px 8px; margin-bottom: 6px;
  border-radius: 999px; background: var(--amber); color: var(--on-accent) !important;
}
@media (max-width: 640px) {
  .ui-hero-sub { display: none; }
  .block-container { padding-left: .75rem !important; padding-right: .75rem !important; }
}
</style>
"""


def inject_css(theme="dark"):
    st.markdown(FONTS, unsafe_allow_html=True)
    st.markdown(BASE_CSS(theme), unsafe_allow_html=True)
    st.markdown(MOBILE_CSS, unsafe_allow_html=True)


def theme_toggle_button(location=st.sidebar):
    current = st.session_state.get("theme", "dark")
    label = "☀️ Chế độ sáng" if current == "dark" else "🌙 Chế độ tối"
    if location.button(label, key="ui-theme-toggle"):
        st.session_state["theme"] = "light" if current == "dark" else "dark"
        st.rerun()
    return st.session_state.get("theme", "dark")


def hero(title, subtitle):
    st.markdown(
        f"""<div class="ui-hero">
            <p class="ui-hero-title">{_html.escape(title)}</p>
            <p class="ui-hero-sub">{_html.escape(subtitle)}</p>
        </div>""",
        unsafe_allow_html=True,
    )


def render_stepper(labels, current_index, placeholder=None):
    parts = ['<div class="ui-stepper">']
    for i, label in enumerate(labels):
        state = "done" if i < current_index else ("active" if i == current_index else "")
        parts.append(f'<div class="ui-step {state}">')
        parts.append(f'<div class="ui-step-dot">{"✓" if state == "done" else i + 1}</div>')
        parts.append(f'<div class="ui-step-label">{_html.escape(label)}</div>')
        if i < len(labels) - 1:
            parts.append('<div class="ui-step-line"></div>')
        parts.append("</div>")
    parts.append("</div>")
    (placeholder or st).markdown("".join(parts), unsafe_allow_html=True)


def chips(items):
    if not items:
        st.caption("Không có.")
        return
    row = "".join(f'<span class="ui-chip">{_html.escape(t)}</span>' for t in items)
    st.markdown(f'<div class="ui-chip-row">{row}</div>', unsafe_allow_html=True)


def equalizer(playing=False, label=""):
    cls = "ui-eq playing" if playing else "ui-eq"
    st.markdown(
        f'<div style="display:flex;align-items:center;">'
        f'<span class="{cls}"><span></span><span></span><span></span><span></span></span>'
        f'<span style="color:var(--muted);font-size:0.85rem;">{_html.escape(label)}</span></div>',
        unsafe_allow_html=True,
    )


def copy_button(text, label="📋 Sao chép nội dung"):
    safe_text = json.dumps(text or "")
    components.html(
        f"""
        <button id="ui-copy-btn" style="
            background:#1A2130;color:#ECEEF2;border:1px solid #2E3850;border-radius:8px;
            padding:8px 14px;font-family:'Be Vietnam Pro',sans-serif;font-weight:600;
            font-size:0.85rem;cursor:pointer;">{_html.escape(label)}</button>
        <span id="ui-copy-msg" style="margin-left:8px;color:#8BB174;font-size:0.8rem;"></span>
        <script>
          const btn = document.getElementById("ui-copy-btn");
          const msg = document.getElementById("ui-copy-msg");
          btn.addEventListener("click", async () => {{
            try {{
              await navigator.clipboard.writeText({safe_text});
              msg.textContent = "Đã sao chép!";
              setTimeout(() => msg.textContent = "", 1800);
            }} catch (e) {{
              msg.textContent = "Trình duyệt chặn sao chép tự động.";
            }}
          }});
        </script>
        """,
        height=40,
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
    """Lưới thống kê. items = [(nhãn, giá trị), ...]."""
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
