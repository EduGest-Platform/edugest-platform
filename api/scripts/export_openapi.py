"""Writes the OpenAPI contract to contracts/openapi.json (source for the generated TS client)."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "contracts" / "openapi.json"


def render() -> str:
    return json.dumps(app.openapi(), indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify the committed OpenAPI contract without modifying it.")
    rendered = render()
    if parser.parse_args().check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != rendered:
            print("OpenAPI desactualizado. Desde api/ ejecuta python -m scripts.export_openapi y después pnpm gen:api desde la raíz.", file=sys.stderr)
            return 1
        print("El contrato OpenAPI coincide con FastAPI.")
        return 0
    OUT.write_text(rendered, encoding="utf-8")
    print(f"OpenAPI escrito en {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
