"""Nhận diện từng trình duyệt/thiết bị để mỗi máy có thư viện bài học riêng.

Cách hoạt động (không cần đăng nhập):
- Lần đầu vào web, app sinh một mã ngẫu nhiên 128 bit (owner_id) và ghi vào cookie
  "la_owner" của trình duyệt (hạn 1 năm).
- Các lần sau, Streamlit đọc cookie này (st.context.cookies) và dùng lại đúng mã đó.
- lesson_store chỉ trả về / cho sửa / cho xóa các bài có owner_id khớp, nên máy khác
  (mã khác) không thấy bài của bạn dù dùng chung một server.

- Dự phòng khi cookie không giữ được (ví dụ app chạy trong iframe trên Streamlit Cloud, chế độ
  ẩn danh): mã còn được ghi vào địa chỉ trang (tham số ?u=...). Mở lại đúng địa chỉ đó (hoặc
  đánh dấu trang) sẽ thấy lại thư viện. Ai có địa chỉ đó cũng xem được thư viện.

Giới hạn cần biết:
- Mã nằm trong cookie: xóa cookie, dùng chế độ ẩn danh hoặc đổi trình duyệt/thiết bị
  sẽ thành "người mới" với thư viện trống (bài cũ vẫn còn trong DB nhưng không ai
  mở lại được).
- Đây là cách tách dữ liệu theo thiết bị, KHÔNG phải tài khoản: ai có được mã (ví dụ
  copy cookie) thì xem được thư viện đó. Không dùng cho dữ liệu nhạy cảm.
- Nếu trình duyệt chặn cookie, mỗi lần tải lại trang sẽ ra một thư viện trống. Dữ liệu
  vẫn không bị lộ cho máy khác.
"""
import json
import re
import uuid

COOKIE_NAME = "la_owner"
QUERY_PARAM = "u"
COOKIE_MAX_AGE = 365 * 24 * 3600  # 1 năm, tính bằng giây
_VALID = re.compile(r"[0-9a-f]{32}")

_SESSION_OWNER = "owner_id"
_SESSION_PENDING = "owner_cookie_pending"


def new_owner_id():
    return uuid.uuid4().hex


def is_valid_owner_id(value):
    """Chỉ chấp nhận đúng định dạng do app sinh ra, tránh giá trị lạ từ cookie giả."""
    return isinstance(value, str) and bool(_VALID.fullmatch(value))


def resolve_owner(cookie_value, fallback_value=None):
    """Trả về (owner_id, can_ghi_cookie).

    Ưu tiên cookie hợp lệ; nếu không có thì dùng giá trị dự phòng (tham số trên địa chỉ trang)
    và vẫn cần ghi cookie; nếu cả hai đều không hợp lệ thì sinh mã mới.
    """
    if is_valid_owner_id(cookie_value):
        return cookie_value, False
    if is_valid_owner_id(fallback_value):
        return fallback_value, True
    return new_owner_id(), True


def _read_query_param():
    import streamlit as st

    try:
        value = st.query_params.get(QUERY_PARAM)
        return value[0] if isinstance(value, list) else value
    except Exception:  # Streamlit cũ chưa có st.query_params
        return None


def _write_query_param(owner_id):
    import streamlit as st

    try:
        if st.query_params.get(QUERY_PARAM) != owner_id:
            st.query_params[QUERY_PARAM] = owner_id
    except Exception:
        pass


def _read_cookie():
    import streamlit as st

    try:
        return st.context.cookies.get(COOKIE_NAME)
    except Exception:  # Streamlit cũ chưa có st.context, hoặc chạy ngoài server
        return None


def get_owner_id():
    """Mã chủ sở hữu của phiên hiện tại. Gọi ở đầu app, trước khi đụng tới lesson_store."""
    import streamlit as st

    if _SESSION_OWNER not in st.session_state:
        owner, needs_cookie = resolve_owner(_read_cookie(), _read_query_param())
        st.session_state[_SESSION_OWNER] = owner
        st.session_state[_SESSION_PENDING] = needs_cookie
    _write_query_param(st.session_state[_SESSION_OWNER])
    return st.session_state[_SESSION_OWNER]


def cookie_setter_html(owner_id):
    """HTML (chỉ chứa script) ghi cookie vào trang chứa app."""
    if not is_valid_owner_id(owner_id):
        raise ValueError("owner_id không hợp lệ")
    cfg = json.dumps({"name": COOKIE_NAME, "value": owner_id, "maxAge": COOKIE_MAX_AGE})
    return (
        "<script>(function(){var C=" + cfg + ";"
        "function put(doc){"
        "var sec=(doc.location&&doc.location.protocol==='https:')?'; Secure':'';"
        "doc.cookie=C.name+'='+C.value+'; Max-Age='+C.maxAge+'; Path=/; SameSite=Lax'+sec;}"
        # iframe của components.html là same-origin với trang Streamlit nên ghi được vào cookie của trang
        "try{put(window.parent.document);}catch(e){try{put(document);}catch(e2){}}"
        "})();</script>"
    )


def persist_cookie():
    """Gọi MỘT LẦN ở cuối main.py. Chỉ ghi cookie khi trình duyệt chưa có (lần đầu).

    st.context.cookies không cập nhật trong cùng phiên nên cờ 'pending' còn nguyên cho
    tới khi mở phiên mới; HTML không đổi giữa các lần chạy lại nên iframe được giữ nguyên.
    """
    import streamlit as st
    import streamlit.components.v1 as components

    if st.session_state.get(_SESSION_PENDING):
        components.html(cookie_setter_html(st.session_state[_SESSION_OWNER]), height=0)