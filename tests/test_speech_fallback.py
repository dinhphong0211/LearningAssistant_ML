import asyncio
import os
import sys
import types

from tts import speech


class _FakeGTTS:
    calls = []

    def __init__(self, text, lang="en", slow=False):
        _FakeGTTS.calls.append((text, lang, slow))
        self.text = text

    def save(self, path):
        with open(path, "wb") as f:
            f.write(b"MP3:" + self.text.encode("utf-8"))


async def _edge_ok(chunk, path, voice, rate, sem, retries=2):
    with open(path, "wb") as f:
        f.write(b"EDGE")


async def _edge_fail(chunk, path, voice, rate, sem, retries=2):
    raise ConnectionError("403 bị chặn")


def _run(tmp_path, edge, **kw):
    saved_edge = speech._synthesize_chunk
    saved_mod = sys.modules.get("gtts")
    speech._synthesize_chunk = edge
    _FakeGTTS.calls = []
    sys.modules["gtts"] = types.SimpleNamespace(gTTS=_FakeGTTS)
    try:
        out = str(tmp_path / "a.mp3")
        asyncio.run(speech.generate_speech_async("Xin chào. Đây là bài thử.", out, **kw))
        return out
    finally:
        speech._synthesize_chunk = saved_edge
        if saved_mod is None:
            sys.modules.pop("gtts", None)
        else:
            sys.modules["gtts"] = saved_mod


def test_edge_used_when_it_works(tmp_path):
    out = _run(tmp_path, _edge_ok)
    assert speech.LAST_ENGINE == "edge-tts"
    assert open(out, "rb").read() == b"EDGE"
    assert _FakeGTTS.calls == []


def test_falls_back_to_gtts_when_edge_fails(tmp_path):
    out = _run(tmp_path, _edge_fail, rate="-20%")
    assert speech.LAST_ENGINE == "gTTS (dự phòng)"
    assert open(out, "rb").read().startswith(b"MP3:")
    assert _FakeGTTS.calls and _FakeGTTS.calls[0][1] == "vi" and _FakeGTTS.calls[0][2] is True   # -20% -> slow


def test_fallback_can_be_disabled(tmp_path):
    try:
        _run(tmp_path, _edge_fail, fallback=False)
    except ConnectionError:
        return
    raise AssertionError("phải ném lỗi khi tắt dự phòng")


def test_missing_gtts_gives_clear_message(tmp_path):
    saved_edge, saved_mod = speech._synthesize_chunk, sys.modules.get("gtts")
    speech._synthesize_chunk = _edge_fail
    sys.modules["gtts"] = None            # import gtts sẽ báo ImportError
    try:
        try:
            asyncio.run(speech.generate_speech_async("Xin chào bạn nhé.", str(tmp_path / "b.mp3")))
        except RuntimeError as e:
            assert "pip install gTTS" in str(e) and "403" in str(e)
            return
        raise AssertionError("phải báo lỗi rõ ràng")
    finally:
        speech._synthesize_chunk = saved_edge
        if saved_mod is None:
            sys.modules.pop("gtts", None)
        else:
            sys.modules["gtts"] = saved_mod
