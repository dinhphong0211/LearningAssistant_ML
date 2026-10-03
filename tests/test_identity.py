import pytest

import identity


def test_new_ids_are_valid_and_unique():
    ids = {identity.new_owner_id() for _ in range(50)}
    assert len(ids) == 50
    assert all(identity.is_valid_owner_id(i) for i in ids)


@pytest.mark.parametrize("bad", [None, "", "abc", "A" * 32, "g" * 32, "a" * 31, "a" * 33, "a" * 32 + "\n", 123])
def test_rejects_malformed_cookie_values(bad):
    assert not identity.is_valid_owner_id(bad)
    owner, needs_cookie = identity.resolve_owner(bad)
    assert identity.is_valid_owner_id(owner) and owner != bad
    assert needs_cookie


def test_valid_cookie_is_reused_without_rewriting():
    existing = "0123456789abcdef" * 2
    assert identity.resolve_owner(existing) == (existing, False)


def test_cookie_setter_html_is_stable_and_safe():
    owner = "0123456789abcdef" * 2
    html = identity.cookie_setter_html(owner)
    assert html == identity.cookie_setter_html(owner)  # không đổi -> iframe được giữ giữa các lần chạy lại
    assert owner in html and identity.COOKIE_NAME in html and "SameSite=Lax" in html
    with pytest.raises(ValueError):
        identity.cookie_setter_html('x"; alert(1); //')
