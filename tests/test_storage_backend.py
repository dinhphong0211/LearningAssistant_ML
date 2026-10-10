import identity
import lesson_store

EXISTING = "0123456789abcdef" * 2


def test_sqlite_when_library_db_is_set(tmp_path, monkeypatch):
    monkeypatch.setenv("LIBRARY_DB", str(tmp_path / "lib.db"))
    monkeypatch.setenv("LIBRARY_DATABASE_URL", "postgresql://u:p@h:5432/db")
    assert lesson_store.backend_name() == "sqlite"
    assert not lesson_store.is_persistent()


def test_postgres_when_url_is_set(monkeypatch):
    monkeypatch.delenv("LIBRARY_DB", raising=False)
    monkeypatch.setenv("LIBRARY_DATABASE_URL", "postgresql://u:p@h:5432/db")
    assert lesson_store.backend_name() == "postgres"
    assert lesson_store.is_persistent()


def test_ssl_is_added_once():
    assert lesson_store._with_ssl("postgresql://u:p@h/db").endswith("?sslmode=require")
    assert lesson_store._with_ssl("postgresql://u:p@h/db?x=1").endswith("&sslmode=require")
    assert lesson_store._with_ssl("postgresql://u:p@h/db?sslmode=disable").count("sslmode") == 1


def test_owner_falls_back_to_query_param():
    assert identity.resolve_owner(None, EXISTING) == (EXISTING, True)
    assert identity.resolve_owner(EXISTING, "b" * 32) == (EXISTING, False)
    owner, needs_cookie = identity.resolve_owner("bad", "also-bad")
    assert identity.is_valid_owner_id(owner) and needs_cookie