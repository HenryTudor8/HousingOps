"""SQL access contract tests: parameter binding, no live Neon connection."""
from datetime import date

import pytest
from app import workflow_repository


def test_workflow_query_uses_parameter_placeholders(monkeypatch):
    recorded = []
    monkeypatch.setattr(
        workflow_repository, "fetch_all",
        lambda statement, params: recorded.append((statement, params)) or [],
    )
    end = date(2027, 5, 15)
    result = workflow_repository.resident_assignments_for_preview("REQ_0001", end)
    assert result == []
    assert recorded[0][1] == ("REQ_0001", end)
    assert recorded[0][0].count("%s") == 2
    assert "REQ_0001" not in recorded[0][0]
    assert "INSERT" not in recorded[0][0]
    assert "UPDATE" not in recorded[0][0]


def test_rejects_invalid_id_before_db(monkeypatch):
    monkeypatch.setattr(
        workflow_repository, "fetch_all", lambda *_: pytest.fail("Database should not be accessed")
    )
    with pytest.raises(ValueError):
        workflow_repository.resident_assignments_for_preview("", date(2027, 5, 15))


def test_rejects_invalid_end_before_db(monkeypatch):
    monkeypatch.setattr(
        workflow_repository, "fetch_all", lambda *_: pytest.fail("Database should not be accessed")
    )
    with pytest.raises(TypeError):
        workflow_repository.resident_assignments_for_preview("REQ_0001", "2027-05-15")


def test_request_context_is_read_only_and_parameterized(monkeypatch):
    got = []
    monkeypatch.setattr(
        workflow_repository, "fetch_all",
        lambda sql, params: got.append((sql, params)) or [{"request_id": "REQ_0001"}],
    )
    row = workflow_repository.request_context_for_preview("REQ_0001")
    assert row == {"request_id": "REQ_0001"}
    assert got[0][1] == ("REQ_0001",)
    assert got[0][0].count("%s") == 1


def test_unknown_request_context_returns_none(monkeypatch):
    monkeypatch.setattr(workflow_repository, "fetch_all", lambda *_: [])
    assert workflow_repository.request_context_for_preview("REQ_UNKNOWN") is None
