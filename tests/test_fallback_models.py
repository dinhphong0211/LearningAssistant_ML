import pytest

from summarization import abstractive
from summarization.abstractive import TransformerSummarizer


class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeModel:
    """Mô phỏng một model Gemini: mỗi lần gọi lấy kết quả (hoặc lỗi) kế tiếp trong kịch bản."""
    calls = {}

    def __init__(self, name):
        self.name = name

    def generate_content(self, prompt):
        FakeModel.calls[self.name] = FakeModel.calls.get(self.name, 0) + 1
        action = SCRIPT[self.name]
        if isinstance(action, Exception):
            raise action
        return FakeResponse(action)


class ResourceExhausted(Exception):
    pass


class NotFound(Exception):
    pass


class PermissionDenied(Exception):
    pass


SCRIPT = {}


@pytest.fixture(autouse=True)
def fake_gemini(monkeypatch):
    FakeModel.calls = {}
    SCRIPT.clear()
    monkeypatch.setattr(abstractive, "configure_gemini", lambda: None)
    monkeypatch.setattr(abstractive.genai, "GenerativeModel", FakeModel)
    monkeypatch.setattr(abstractive.time, "sleep", lambda s: None)


def make(primary="primary", fallbacks=("gemini-3.8-flash", "gemini-3.5-flash-lite")):
    return TransformerSummarizer(primary, fallback_models=fallbacks, retry_delays=(1, 1))


def test_default_fallbacks_are_38_flash_then_35_flash_lite():
    assert abstractive.FALLBACK_MODELS == ("gemini-3.8-flash", "gemini-3.5-flash-lite")
    s = TransformerSummarizer("primary")
    assert s.fallback_models == ["gemini-3.8-flash", "gemini-3.5-flash-lite"]


def test_primary_is_removed_from_its_own_fallbacks():
    s = TransformerSummarizer("gemini-3.8-flash")
    assert s.fallback_models == ["gemini-3.5-flash-lite"]


def test_empty_tuple_disables_fallbacks():
    assert TransformerSummarizer("primary", fallback_models=()).fallback_models == []


def test_env_overrides_fallbacks(monkeypatch):
    monkeypatch.setenv("GEMINI_FALLBACK_MODELS", " models/x-1 , y-2,x-1")
    assert abstractive.get_fallback_models() == ("x-1", "y-2")


def test_rate_limit_retries_then_falls_back_in_order():
    SCRIPT.update({"primary": ResourceExhausted("429 quota"), "gemini-3.8-flash": "ok 3.8", "gemini-3.5-flash-lite": "never"})
    s = make()
    assert s._generate("hi") == "ok 3.8"
    assert s.last_used_model == "gemini-3.8-flash"
    assert FakeModel.calls == {"primary": 3, "gemini-3.8-flash": 1}  # 1 lần + 2 lần thử lại


def test_second_fallback_used_when_first_also_limited():
    SCRIPT.update({"primary": ResourceExhausted("429"), "gemini-3.8-flash": ResourceExhausted("429"), "gemini-3.5-flash-lite": "ok lite"})
    s = make()
    assert s._generate("hi") == "ok lite"
    assert s.last_used_model == "gemini-3.5-flash-lite"


def test_missing_model_skips_immediately_without_retry():
    SCRIPT["primary"] = NotFound("404 models/primary is not found")
    SCRIPT["gemini-3.8-flash"] = NotFound("404 models/gemini-3.8-flash is not found")
    SCRIPT["gemini-3.5-flash-lite"] = "ok lite"
    s = make()
    assert s._generate("hi") == "ok lite"
    assert FakeModel.calls == {"primary": 1, "gemini-3.8-flash": 1, "gemini-3.5-flash-lite": 1}


def test_overloaded_503_is_retried_like_rate_limit():
    SCRIPT.update({"primary": Exception("503 The model is overloaded"), "gemini-3.8-flash": "ok"})
    assert make()._generate("hi") == "ok"


def test_other_errors_are_raised_immediately():
    SCRIPT.update({"primary": PermissionDenied("API key not valid"), "gemini-3.8-flash": "never"})
    with pytest.raises(PermissionDenied):
        make()._generate("hi")
    assert FakeModel.calls == {"primary": 1}


def test_all_models_exhausted_raises_last_error():
    for name in ("primary", "gemini-3.8-flash", "gemini-3.5-flash-lite"):
        SCRIPT[name] = ResourceExhausted(f"429 {name}")
    with pytest.raises(ResourceExhausted, match="gemini-3.5-flash-lite"):
        make()._generate("hi")
