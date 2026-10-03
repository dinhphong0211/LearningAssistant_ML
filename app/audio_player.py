"""Trình phát audio chạy ở phía trình duyệt, tối ưu cho điện thoại.

Tính năng:
- Lưu vị trí nghe vào localStorage (theo id bài) mỗi ~2 giây, khi tạm dừng,
  khi chuyển tab/khóa màn hình và khi đóng trang. Mở lại bài sẽ tự tua tới đúng chỗ.
- Media Session API: hiện tên bài và nút phát/tạm dừng/tua trên màn hình khóa
  và thông báo của hệ điều hành, nên nghe tiếp được khi tắt màn hình.
- Nút lùi/tiến 15 giây, chọn tốc độ, hẹn giờ tắt.

Trình phát nằm trong một iframe (components.html). Miễn là HTML truyền vào không
đổi giữa các lần chạy lại, Streamlit giữ nguyên iframe nên audio không bị ngắt khi
bấm nút khác hoặc chuyển tab con.

Lưu ý: vị trí nghe gắn với trình duyệt/thiết bị đang dùng, không đồng bộ giữa
điện thoại và máy tính.
"""
import base64
import json

DEFAULT_PALETTE = {
    "surface": "#1A2130", "surface-raised": "#212A3D", "rule": "#2E3850",
    "amber": "#E3A23D", "sage": "#8BB174", "text": "#ECEEF2",
    "muted": "#96A0B5", "on-accent": "#11151C",
}

_TEMPLATE = r"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root { __VARS__ }
* { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
html, body { margin: 0; background: transparent; color: var(--text);
  font-family: "Be Vietnam Pro", system-ui, -apple-system, "Segoe UI", sans-serif; }
.card { background: var(--surface-raised); border: 1px solid var(--rule);
  border-left: 3px solid var(--amber); border-radius: 14px; padding: 14px 14px 12px; }
.title { font-weight: 700; font-size: 1rem; line-height: 1.3;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.msg { color: var(--muted); font-size: .8rem; min-height: 1.1em; margin: 4px 0 8px; }
input[type=range] { width: 100%; height: 32px; margin: 0; accent-color: var(--amber); }
.times { display: flex; justify-content: space-between; color: var(--muted);
  font-size: .78rem; font-variant-numeric: tabular-nums; margin-top: -2px; }
.ctl { display: flex; align-items: center; justify-content: center; gap: 14px; margin: 10px 0 8px; }
button { font: inherit; color: var(--text); background: var(--surface); border: 1px solid var(--rule);
  border-radius: 12px; min-height: 48px; padding: 0 14px; font-weight: 600; cursor: pointer; }
button:active { transform: scale(.97); }
button.big { width: 68px; height: 68px; border-radius: 50%; font-size: 1.6rem; padding: 0;
  background: var(--sage); color: var(--on-accent); border: none; }
.opt { display: flex; gap: 8px; }
.opt button { flex: 1; min-height: 44px; font-size: .85rem; }
</style></head><body>
<div class="card">
  <div class="title" id="title"></div>
  <div class="msg" id="msg">Đang tải audio…</div>
  <input type="range" id="seek" min="0" max="100" step="1" value="0" aria-label="Thanh tua">
  <div class="times"><span id="cur">00:00</span><span id="dur">--:--</span></div>
  <div class="ctl">
    <button id="back" aria-label="Lùi 15 giây">⟲ 15</button>
    <button id="play" class="big" aria-label="Phát">▶</button>
    <button id="fwd" aria-label="Tiến 15 giây">15 ⟳</button>
  </div>
  <div class="opt">
    <button id="speed" aria-label="Tốc độ">1×</button>
    <button id="sleep" aria-label="Hẹn giờ tắt">😴 Hẹn giờ: tắt</button>
  </div>
  <audio id="a" preload="metadata"></audio>
</div>
<script>
(function () {
  var CFG = __CFG__;
  var B64 = "__B64__";
  var KEY = "la:pos:" + CFG.id;
  var RATES = [0.75, 1, 1.25, 1.5, 1.75, 2];
  var SLEEPS = [0, 15, 30, 60];
  var SKIP = 15;

  function $(id) { return document.getElementById(id); }
  var audio = $("a"), elMsg = $("msg"), elSeek = $("seek"), elCur = $("cur"), elDur = $("dur");
  var btnPlay = $("play"), btnBack = $("back"), btnFwd = $("fwd"), btnSpeed = $("speed"), btnSleep = $("sleep");
  $("title").textContent = CFG.title;

  function fmt(s) {
    if (!isFinite(s) || s < 0) s = 0;
    s = Math.floor(s);
    var h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), c = s % 60;
    var mm = (m < 10 ? "0" : "") + m, ss = (c < 10 ? "0" : "") + c;
    return h > 0 ? h + ":" + mm + ":" + ss : mm + ":" + ss;
  }
  function loadSaved() {
    try { var raw = localStorage.getItem(KEY); return raw ? JSON.parse(raw) : null; }
    catch (e) { return null; }
  }
  function store(o) { try { localStorage.setItem(KEY, JSON.stringify(o)); } catch (e) {} }
  function say(t) { elMsg.textContent = t; }
  function dur() { return isFinite(audio.duration) ? audio.duration : 0; }

  var ready = false;      // chỉ lưu vị trí sau khi đã khôi phục xong, tránh ghi đè bằng 0
  var dragging = false;
  var lastSave = 0, lastPos = 0;
  var rate = 1;
  var sleepIdx = 0, sleepTimer = null;

  var saved = loadSaved();
  if (saved && saved.rate && RATES.indexOf(saved.rate) >= 0) rate = saved.rate;

  // Giải mã audio thành Blob để tua được và không phải tải lại
  var bin = atob(B64), bytes = new Uint8Array(bin.length);
  for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  audio.src = URL.createObjectURL(new Blob([bytes], { type: "audio/mpeg" }));
  audio.defaultPlaybackRate = rate;
  audio.playbackRate = rate;
  btnSpeed.textContent = rate + "×";

  function persist(force) {
    if (!ready) return;
    var now = Date.now();
    if (!force && now - lastSave < 2000) return;
    lastSave = now;
    store({ t: audio.currentTime, d: dur(), rate: rate, ts: now });
  }

  function refresh() {
    var d = dur();
    if (!dragging) {
      elSeek.max = d || 100;
      elSeek.value = audio.currentTime;
      elCur.textContent = fmt(audio.currentTime);
    }
    elDur.textContent = d ? fmt(d) : "--:--";
  }

  function updatePositionState() {
    if (!("mediaSession" in navigator) || !navigator.mediaSession.setPositionState) return;
    var d = dur();
    if (!d) return;
    try {
      navigator.mediaSession.setPositionState({
        duration: d, playbackRate: audio.playbackRate || 1,
        position: Math.min(Math.max(audio.currentTime, 0), d)
      });
    } catch (e) {}
  }

  function seekBy(delta) {
    var d = dur();
    var t = audio.currentTime + delta;
    if (t < 0) t = 0;
    if (d && t > d) t = d;
    audio.currentTime = t;
    refresh(); persist(true); updatePositionState();
  }
  function toggle() {
    if (audio.paused) {
      var p = audio.play();
      if (p && p.catch) p.catch(function () { say("Trình duyệt chặn phát tự động, hãy bấm ▶ lần nữa."); });
    } else {
      audio.pause();
    }
  }

  audio.addEventListener("loadedmetadata", function () {
    var s = loadSaved(), d = dur();
    if (s && !s.done && s.t > 1 && (!d || s.t < d - 2)) {
      audio.currentTime = s.t;
      say("Đã khôi phục vị trí " + fmt(s.t) + " · nhấn ▶ để nghe tiếp");
    } else if (s && s.done) {
      say("Lần trước đã nghe xong · nhấn ▶ để nghe lại từ đầu");
    } else {
      say("Nhấn ▶ để bắt đầu nghe");
    }
    ready = true;
    refresh(); updatePositionState();
  });
  audio.addEventListener("error", function () { say("Không phát được file audio này."); });
  audio.addEventListener("timeupdate", function () {
    refresh(); persist(false);
    var now = Date.now();
    if (now - lastPos > 5000) { lastPos = now; updatePositionState(); }
  });
  audio.addEventListener("play", function () {
    btnPlay.textContent = "⏸"; btnPlay.setAttribute("aria-label", "Tạm dừng");
    if ("mediaSession" in navigator) navigator.mediaSession.playbackState = "playing";
    if (ready) say("Đang phát");
  });
  audio.addEventListener("pause", function () {
    btnPlay.textContent = "▶"; btnPlay.setAttribute("aria-label", "Phát");
    if ("mediaSession" in navigator) navigator.mediaSession.playbackState = "paused";
    if (!audio.ended) { persist(true); if (ready) say("Đã tạm dừng ở " + fmt(audio.currentTime)); }
  });
  audio.addEventListener("ended", function () {
    store({ t: 0, d: dur(), rate: rate, ts: Date.now(), done: true });
    say("Đã nghe xong · lần sau sẽ bắt đầu lại từ đầu");
  });

  btnPlay.addEventListener("click", toggle);
  btnBack.addEventListener("click", function () { seekBy(-SKIP); });
  btnFwd.addEventListener("click", function () { seekBy(SKIP); });

  elSeek.addEventListener("input", function () {
    dragging = true; elCur.textContent = fmt(Number(elSeek.value));
  });
  elSeek.addEventListener("change", function () {
    audio.currentTime = Number(elSeek.value);
    dragging = false; refresh(); persist(true); updatePositionState();
  });

  btnSpeed.addEventListener("click", function () {
    var idx = RATES.indexOf(rate);
    rate = RATES[(idx + 1) % RATES.length];
    audio.defaultPlaybackRate = rate;
    audio.playbackRate = rate;
    btnSpeed.textContent = rate + "×";
    persist(true); updatePositionState();
  });

  btnSleep.addEventListener("click", function () {
    sleepIdx = (sleepIdx + 1) % SLEEPS.length;
    if (sleepTimer) { clearTimeout(sleepTimer); sleepTimer = null; }
    var mins = SLEEPS[sleepIdx];
    if (mins > 0) {
      sleepTimer = setTimeout(function () {
        audio.pause(); sleepIdx = 0; sleepTimer = null;
        btnSleep.textContent = "😴 Hẹn giờ: tắt";
        say("Đã dừng theo hẹn giờ");
      }, mins * 60 * 1000);
      btnSleep.textContent = "😴 Tắt sau " + mins + " phút";
    } else {
      btnSleep.textContent = "😴 Hẹn giờ: tắt";
    }
  });

  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "hidden") persist(true);
  });
  window.addEventListener("pagehide", function () { persist(true); });

  // Điều khiển trên màn hình khóa / thông báo
  if ("mediaSession" in navigator) {
    try {
      navigator.mediaSession.metadata = new MediaMetadata({
        title: CFG.title, artist: "Trợ Lý Học Tập Thông Minh", album: "Thư viện bài học"
      });
    } catch (e) {}
    var set = function (name, fn) { try { navigator.mediaSession.setActionHandler(name, fn); } catch (e) {} };
    set("play", function () { if (audio.paused) toggle(); });
    set("pause", function () { if (!audio.paused) toggle(); });
    set("seekbackward", function (d) { seekBy(-((d && d.seekOffset) || SKIP)); });
    set("seekforward", function (d) { seekBy((d && d.seekOffset) || SKIP); });
    set("previoustrack", function () { seekBy(-SKIP); });
    set("nexttrack", function () { seekBy(SKIP); });
    set("seekto", function (d) {
      if (d && typeof d.seekTime === "number") {
        audio.currentTime = d.seekTime; refresh(); persist(true); updatePositionState();
      }
    });
  }
})();
</script></body></html>
"""


def _vars(palette):
    p = {**DEFAULT_PALETTE, **(palette or {})}
    return " ".join(f"--{k}: {v};" for k, v in p.items())


def _safe_json(obj):
    # Không để chuỗi "</script>" trong tiêu đề làm vỡ thẻ script
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def build_html(lesson_id, title, audio_bytes, palette=None):
    b64 = base64.b64encode(audio_bytes).decode("ascii")
    cfg = _safe_json({"id": str(lesson_id), "title": title or "Bài học"})
    return (
        _TEMPLATE
        .replace("__VARS__", _vars(palette))
        .replace("__CFG__", cfg)
        .replace("__B64__", b64)
    )


def render(lesson_id, title, audio_bytes, palette=None, height=270):
    import streamlit.components.v1 as components

    components.html(build_html(lesson_id, title, audio_bytes, palette), height=height)
