"""Regression tests for the OpenAPI export command without touching the real contract."""

import sys

import pytest

from scripts import export_openapi


@pytest.mark.parametrize("existing, expected", [(None, 1), ("stale\n", 1), ('{"openapi": "3.1.0"}\n', 0)])
def test_check_does_not_write(tmp_path, monkeypatch, existing, expected):
    target = tmp_path / "openapi.json"
    if existing is not None:
        target.write_text(existing, encoding="utf-8")
    monkeypatch.setattr(export_openapi, "OUT", target)
    monkeypatch.setattr(export_openapi, "render", lambda: '{"openapi": "3.1.0"}\n')
    monkeypatch.setattr(sys, "argv", ["export_openapi", "--check"])

    assert export_openapi.main() == expected
    if existing is None:
        assert not target.exists()
    else:
        assert target.read_text(encoding="utf-8") == existing


def test_export_then_check(tmp_path, monkeypatch):
    target = tmp_path / "openapi.json"
    monkeypatch.setattr(export_openapi, "OUT", target)
    monkeypatch.setattr(export_openapi, "render", lambda: '{"openapi": "3.1.0"}\n')
    monkeypatch.setattr(sys, "argv", ["export_openapi"])
    assert export_openapi.main() == 0
    assert target.read_text(encoding="utf-8") == '{"openapi": "3.1.0"}\n'
    monkeypatch.setattr(sys, "argv", ["export_openapi", "--check"])
    assert export_openapi.main() == 0


def test_render_is_deterministic(monkeypatch):
    monkeypatch.setattr(export_openapi.app, "openapi", lambda: {"z": "matrícula", "a": 1})
    assert export_openapi.render() == '{\n  "a": 1,\n  "z": "matrícula"\n}\n'


def test_check_reports_removed_operation_without_rewriting(tmp_path, monkeypatch):
    target = tmp_path / "openapi.json"
    existing = '{"paths": {"/example": {"get": {}}}}\n'
    target.write_text(existing, encoding="utf-8")
    monkeypatch.setattr(export_openapi, "OUT", target)
    monkeypatch.setattr(export_openapi, "render", lambda: '{"paths": {}}\n')
    monkeypatch.setattr(sys, "argv", ["export_openapi", "--check"])
    assert export_openapi.main() == 1
    assert target.read_text(encoding="utf-8") == existing
