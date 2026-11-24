"""Publish aggregate test evidence without copying JUnit messages or test identities."""

import argparse
import json
import re
from pathlib import Path
from xml.etree import ElementTree

FIELDS = ("tests", "failures", "errors", "skipped")


def summarize(report: Path, outcome: str, commit: str) -> dict:
    result = {"schema_version": 1, "commit": commit if re.fullmatch(r"[0-9a-f]{40}", commit) else None,
              "check_outcome": outcome, "status": "unavailable", "counts": None}
    if not report.is_file():
        return result
    try:
        root = ElementTree.parse(report).getroot()
        suites = [root] if root.tag == "testsuite" else list(root) if root.tag == "testsuites" else []
        if not suites or any(suite.tag != "testsuite" or suite.findall(".//testsuite") for suite in suites):
            raise ValueError("Unsupported suite layout")
        counts = dict.fromkeys(FIELDS, 0)
        for suite in suites:
            values = {}
            for field in FIELDS:
                raw = suite.attrib[field]
                if not re.fullmatch(r"[0-9]{1,10}", raw):
                    raise ValueError("Invalid count")
                values[field] = int(raw)
            if sum(values[field] for field in FIELDS[1:]) > values["tests"]:
                raise ValueError("Inconsistent counts")
            for field, value in values.items():
                counts[field] += value
        counts["passed"] = counts["tests"] - sum(counts[field] for field in FIELDS[1:])
        result["counts"] = counts
        result["status"] = "passed" if (
            outcome == "success" and result["commit"] and counts["passed"] > 0
            and counts["failures"] == counts["errors"] == 0
        ) else "failed"
    except (OSError, ElementTree.ParseError, KeyError, ValueError):
        # Never echo malformed XML, paths, exception details or captured test output.
        result["status"] = "invalid"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--outcome", choices=["success", "failure", "cancelled", "skipped"], required=True)
    parser.add_argument("--suite", choices=["api", "web"], default="api")
    args = parser.parse_args()
    result = summarize(args.input, args.outcome, args.commit)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    label = args.suite.upper()
    lines = [f"## {label} test evidence / Evidencia de pruebas {label}", "", f"Status / Estado: **{result['status']}**", "",
             "Only aggregate counts; no test identities or output. / Solo totales, sin nombres ni salida de tests.", ""]
    if result["counts"] is not None:
        lines += ["| Metric / Métrica | Count / Total |", "|---|---|"]
        lines += [f"| {key} | {value} |" for key, value in result["counts"].items()]
    else:
        lines += ["No usable report; this is not passing evidence. / Sin informe utilizable; no acredita éxito."]
    with args.summary.open("a", encoding="utf-8") as stream:
        stream.write("\n".join(lines) + "\n")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
