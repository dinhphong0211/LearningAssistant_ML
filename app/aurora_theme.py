"""Aurora theme cho Streamlit: nền đa sắc chuyển động ~8s rồi đứng yên.

Cách dùng (trong file app chính, ngay sau st.set_page_config):

    from aurora_theme import apply_aurora_theme
    apply_aurora_theme()
"""

import streamlit as st

AURORA_CSS = """
<style>
/* Cho phép animate các biến vị trí/góc (Chrome/Edge hỗ trợ) */
@property --ax { syntax: "<percentage>"; inherits: true; initial-value: 12%; }
@property --ay { syntax: "<percentage>"; inherits: true; initial-value: 8%; }
@property --bx { syntax: "<percentage>"; inherits: true; initial-value: 88%; }
@property --by { syntax: "<percentage>"; inherits: true; initial-value: 18%; }
@property --cx { syntax: "<percentage>"; inherits: true; initial-value: 75%; }
@property --cy { syntax: "<percentage>"; inherits: true; initial-value: 92%; }
@property --dx { syntax: "<percentage>"; inherits: true; initial-value: 15%; }
@property --dy { syntax: "<percentage>"; inherits: true; initial-value: 85%; }
@property --ang { syntax: "<angle>"; inherits: true; initial-value: 360deg; }
@property --sweep { syntax: "<number>"; inherits: true; initial-value: 0; }

.stApp {
  background-color: #f7f8fc !important;
  background-image:
    /* vệt sáng quét một vòng rồi mờ dần */
    conic-gradient(from var(--ang) at 55% 40%,
      transparent 0deg,
      rgba(56, 189, 248, calc(.30 * var(--sweep))) 50deg,
      transparent 110deg,
      rgba(244, 114, 182, calc(.30 * var(--sweep))) 200deg,
      transparent 270deg),
    /* các đốm màu kiểu aurora */
    radial-gradient(45% 55% at var(--ax) var(--ay), rgba(66, 133, 244, .45), transparent 70%),
    radial-gradient(40% 50% at var(--bx) var(--by), rgba(155, 114, 203, .45), transparent 70%),
    radial-gradient(45% 50% at var(--cx) var(--cy), rgba(244, 114, 142, .40), transparent 70%),
    radial-gradient(35% 45% at var(--dx) var(--dy), rgba(251, 191, 36, .35), transparent 70%),
    radial-gradient(30% 40% at 50% 55%, rgba(45, 212, 191, .22), transparent 70%) !important;
  background-attachment: fixed !important;
  animation: aurora-intro 8s cubic-bezier(.22, .61, .36, 1) 1 forwards;
}

@keyframes aurora-intro {
  0% {
    --ax: 0%;   --ay: 100%;
    --bx: 100%; --by: 100%;
    --cx: 0%;   --cy: 0%;
    --dx: 100%; --dy: 0%;
    --ang: 0deg; --sweep: 1;
  }
  100% {
    --ax: 12%;  --ay: 8%;
    --bx: 88%;  --by: 18%;
    --cx: 75%;  --cy: 92%;
    --dx: 15%;  --dy: 85%;
    --ang: 360deg; --sweep: 0;
  }
}

/* Để nền lộ ra */
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stHeader"] {
  background: transparent !important;
}

/* Sidebar kính mờ */
section[data-testid="stSidebar"] {
  background: rgba(255, 255, 255, .55) !important;
  backdrop-filter: blur(18px) saturate(1.4);
  -webkit-backdrop-filter: blur(18px) saturate(1.4);
  border-right: 1px solid rgba(255, 255, 255, .6);
}

/* Thẻ nội dung: trắng mờ nhẹ cho dễ đọc */
div[data-testid="stVerticalBlockBorderWrapper"] {
  background: rgba(255, 255, 255, .72);
  backdrop-filter: blur(10px);
  border-radius: 16px !important;
}

/* Tắt chuyển động nếu hệ điều hành yêu cầu giảm hiệu ứng */
@media (prefers-reduced-motion: reduce) {
  .stApp { animation: none !important; }
}
</style>
"""


def apply_aurora_theme() -> None:
    """Chèn CSS nền aurora vào trang. Gọi một lần ở đầu mỗi lần chạy script."""
    st.markdown(AURORA_CSS, unsafe_allow_html=True)