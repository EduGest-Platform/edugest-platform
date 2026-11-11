from pathlib import Path

from app.main import app
from scripts.export_openapi import OUT, render

PUBLIC = {("/api/v1/applications", "post"), ("/api/v1/calls", "get"), ("/api/v1/auth/login", "post"), ("/health", "get")}


def test_committed_contract_matches_api():
    assert Path(OUT).read_text(encoding="utf-8") == render(), "Contrato desactualizado: ejecuta python scripts/export_openapi.py y pnpm gen:api"


def test_private_operations_declare_bearer_security():
    spec = app.openapi()
    for path, ops in spec["paths"].items():
        for method, op in ops.items():
            if (path, method) in PUBLIC:
                continue
            assert op.get("security"), f"{method.upper()} {path} no declara autenticación"
