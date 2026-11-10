"""SQL contract tests using fake connections, no Neon network required."""
from datetime import date
import pytest
from app import repository


def test_missing_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(repository, "load_dotenv", lambda *_a, **_kw: None)
    with pytest.raises(repository.DatabaseNotConfigured):
        repository.database_url()


def test_fetch_all_sets_read_only_before_query(monkeypatch):
    observed = []

    class FakeCursor:
        def __enter__(self):
            return self
        def __exit__(self, *_exc):
            return False
        def execute(self, statement, params=None):
            observed.append((statement, params))
        def fetchall(self):
            return [{"value": 3}]

    class FakeConnection:
        def __enter__(self):
            return self
        def __exit__(self, *_exc):
            return False
        def cursor(self):
            return FakeCursor()

    monkeypatch.setattr(repository, "database_url", lambda: "dummy-do-not-connect")
    monkeypatch.setattr(repository.psycopg, "connect", lambda *_a, **_kw: FakeConnection())
    assert repository.fetch_all("SELECT %s AS value", (3,)) == [{"value": 3}]
    assert observed == [("SET TRANSACTION READ ONLY", None), ("SELECT %s AS value", (3,))]


def test_inventory_date_is_parameterized(monkeypatch):
    called = []
    monkeypatch.setattr(repository, "fetch_all", lambda sql, params=(): called.append((sql, params)) or [])
    target = date(2026, 11, 10)
    repository.inventory_on(target)
    assert called[0][1] == (target, target)
    assert "%s" in called[0][0]


def test_ra_date_is_parameterized(monkeypatch):
    called = []
    monkeypatch.setattr(repository, "fetch_all", lambda sql, params=(): called.append(params) or [])
    target = date(2026, 10, 28)
    repository.ra_coverage_on(target)
    assert called == [(target, target)]


def test_matching_parameters(monkeypatch):
    called = []
    monkeypatch.setattr(repository, "fetch_all", lambda sql, params=(): called.append((sql, params)) or [])
    end = date(2027, 5, 15)
    repository.matching_beds("REQ_0001", date(2026, 10, 28), end)
    assert called[0][1] == ("REQ_0001", end, end)
    assert "REQ_0001" not in called[0][0]
    assert called[0][0].count("%s") == 3


def test_matching_rejects_empty_stay_without_database(monkeypatch):
    monkeypatch.setattr(repository, "fetch_all", lambda *_a: pytest.fail("query should not execute"))
    with pytest.raises(ValueError):
        repository.matching_beds("REQ_0001", date(2027, 5, 15), date(2027, 5, 15))


def test_matching_rejects_empty_id(monkeypatch):
    monkeypatch.setattr(repository, "fetch_all", lambda *_a: pytest.fail("query should not execute"))
    with pytest.raises(ValueError):
        repository.matching_beds("", date(2026, 10, 28), date(2027, 5, 15))


def test_vacancy_checkpoints_use_four_dates(monkeypatch):
    seen = []
    def fake_inventory(day):
        seen.append(day)
        return [{"building_name": "Pride Hall", "available_beds": 1, "total_beds": 2, "occupied_beds": 1}]
    monkeypatch.setattr(repository, "inventory_on", fake_inventory)
    result = repository.vacancy_checkpoints(date(2026, 10, 28))
    assert len(result) == 4
    assert len(seen) == 4
    assert result[-1]["checkpoint"] == "+30 days"
