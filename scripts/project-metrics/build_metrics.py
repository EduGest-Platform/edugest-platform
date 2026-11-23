#!/usr/bin/env python3
"""Build a read-only Jira/GitHub project metrics snapshot for EduGest."""
from __future__ import annotations

import base64
import html
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = os.getenv("GITHUB_REPOSITORY", "EduGest-Platform/edugest-platform")
JIRA_BASE = os.environ["JIRA_BASE_URL"].rstrip("/")
JIRA_EMAIL = os.environ["JIRA_EMAIL"]
JIRA_TOKEN = os.environ["JIRA_API_TOKEN"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
PROJECT_LABEL = os.getenv("JIRA_SCOPE_LABEL", "pf2-v41")
PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY", "KAN")
SPRINT_PREFIX = os.getenv("JIRA_SPRINT_PREFIX", "v41-s")
DONE_STATUS = os.getenv("JIRA_DONE_STATUS", "Finalizada")
OUT = Path(os.getenv("METRICS_OUTPUT_DIR", "dist/project-metrics"))

def request_json(url: str, headers: dict[str, str]) -> dict | list:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read(500).decode("utf-8", "replace")
        raise RuntimeError(f"API request failed ({exc.code}) for {url}: {detail}") from exc

def jira_issues() -> list[dict]:
    token = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_TOKEN}".encode()).decode()
    headers = {"Authorization": f"Basic {token}", "Accept": "application/json"}
    jql = f'project = {PROJECT_KEY} AND issuetype in subTaskIssueTypes() AND labels = "{PROJECT_LABEL}" ORDER BY key ASC'
    fields = "summary,status,labels,issuetype,updated"
    page_token = None
    found: list[dict] = []
    while True:
        params = {"jql": jql, "maxResults": "100", "fields": fields}
        if page_token:
            params["nextPageToken"] = page_token
        url = f"{JIRA_BASE}/rest/api/3/search/jql?{urllib.parse.urlencode(params)}"
        payload = request_json(url, headers)
        batch = payload.get("issues", [])
        found.extend(batch)
        page_token = payload.get("nextPageToken")
        if not page_token:
            break
    return found

def github_get(path: str) -> dict | list:
    return request_json(f"https://api.github.com/repos/{REPO}/{path}", {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })

def build() -> dict:
    issues = jira_issues()
    by_status = Counter()
    sprint_assigned_by_status = Counter()
    by_sprint: dict[str, Counter] = defaultdict(Counter)
    sprint_total = 0
    for issue in issues:
        fields = issue.get("fields", {})
        status = fields.get("status", {}).get("name", "Desconocido")
        labels = fields.get("labels", [])
        by_status[status] += 1
        sprint_labels = sorted(label for label in labels if label.startswith(SPRINT_PREFIX))
        if sprint_labels:
            sprint = sprint_labels[0]
            by_sprint[sprint][status] += 1
            sprint_assigned_by_status[status] += 1
            sprint_total += 1
        else:
            by_sprint["Sin sprint"][status] += 1

    prs = github_get("pulls?state=open&base=dev&per_page=100")
    runs_payload = github_get("actions/runs?branch=dev&per_page=100")
    runs = runs_payload.get("workflow_runs", [])
    latest_by_workflow = {}
    for run in runs:
        name = run.get("name", "Workflow")
        if name not in latest_by_workflow:
            latest_by_workflow[name] = {
                "name": name, "status": run.get("status"),
                "conclusion": run.get("conclusion"),
                "updated_at": run.get("updated_at"),
                "url": run.get("html_url"),
                "sha": (run.get("head_sha") or "")[:8],
            }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository": REPO,
        "jira": {
            "project": PROJECT_KEY, "scope_label": PROJECT_LABEL,
            "total": len(issues), "sprint_assigned": sprint_total,
            "without_sprint": len(issues) - sprint_total,
            "done_status": DONE_STATUS, "by_status": dict(sorted(by_status.items())),
            "sprint_assigned_by_status": dict(sorted(sprint_assigned_by_status.items())),
            "sprints": {
                name: {"total": sum(counts.values()), "by_status": dict(sorted(counts.items()))}
                for name, counts in sorted(by_sprint.items())
            },
            "issues": [
                {"key": issue["key"], "summary": issue.get("fields", {}).get("summary", ""),
                 "status": issue.get("fields", {}).get("status", {}).get("name", "Desconocido"),
                 "labels": issue.get("fields", {}).get("labels", [])}
                for issue in issues
            ],
        },
        "github": {
            "open_prs_to_dev": len(prs),
            "pull_requests": [
                {"number": pr["number"], "title": pr["title"], "url": pr["html_url"],
                 "head": pr["head"]["ref"], "updated_at": pr["updated_at"]}
                for pr in prs
            ],
            "latest_workflows_on_dev": list(latest_by_workflow.values()),
        },
        "definitions": {
            "administrative_completion": f"issues with Jira status exactly '{DONE_STATUS}' divided by sprint-assigned issues",
            "scope": f"Jira subtasks in project {PROJECT_KEY} with label {PROJECT_LABEL}",
            "technical_progress": None,
            "technical_progress_note": "Not calculated: requires a reviewed, evidence-backed acceptance rubric per sprint. PR counts and CI status are not substitutes.",
        },
    }

def render_html(data: dict) -> str:
    jira, gh = data["jira"], data["github"]
    done = jira["sprint_assigned_by_status"].get(DONE_STATUS, 0)
    total = jira["sprint_assigned"]
    pct = (done / total * 100) if total else 0
    sprint_rows = []
    for name, item in jira["sprints"].items():
        states = ", ".join(f"{html.escape(k)}: {v}" for k, v in item["by_status"].items())
        sprint_rows.append(f"<tr><td>{html.escape(name)}</td><td>{item['total']}</td><td>{item['by_status'].get(DONE_STATUS, 0)}</td><td>{states}</td></tr>")
    pr_rows = "".join(f'<li><a href="{html.escape(p["url"], quote=True)}">#{p["number"]} {html.escape(p["title"])}</a> — {html.escape(p["head"])}</li>' for p in gh["pull_requests"]) or "<li>No hay PR abiertas hacia dev.</li>"
    workflow_rows = "".join(f'<tr><td>{html.escape(w["name"])}</td><td>{html.escape(str(w["status"]))}</td><td>{html.escape(str(w["conclusion"]))}</td><td>{html.escape(w["sha"])}</td><td><a href="{html.escape(w["url"], quote=True)}">Ver ejecución</a></td></tr>' for w in gh["latest_workflows_on_dev"])
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>EduGest · Métricas del proyecto</title><style>
:root{{font-family:Inter,system-ui,sans-serif;color:#172033;background:#f4f6fa}}body{{max-width:1100px;margin:32px auto;padding:0 18px}}
header,.card{{background:white;border:1px solid #e3e8f0;border-radius:14px;padding:22px;margin-bottom:18px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px}}.metric{{font-size:2rem;font-weight:750;margin:8px 0}}
small,.muted{{color:#667085}}table{{width:100%;border-collapse:collapse}}th,td{{padding:10px;text-align:left;border-bottom:1px solid #e7ebf2;font-size:.92rem}}
a{{color:#175cd3}}.note{{background:#fff7e6;border:1px solid #f5d58a;padding:12px;border-radius:10px}}
</style></head><body>
<header><h1>EduGest · Estado del proyecto</h1><p class="muted">Generado: {html.escape(data["generated_at"])} · Solo lectura · Fuente: Jira + GitHub</p></header>
<section class="grid">
<div class="card"><div class="muted">Subtareas en alcance Jira</div><div class="metric">{jira["total"]}</div></div>
<div class="card"><div class="muted">Finalizadas / asignadas a sprint</div><div class="metric">{done}/{total}</div><strong>{pct:.1f}%</strong></div>
<div class="card"><div class="muted">Sin sprint</div><div class="metric">{jira["without_sprint"]}</div></div>
<div class="card"><div class="muted">PR abiertas hacia dev</div><div class="metric">{gh["open_prs_to_dev"]}</div></div>
</section>
<section class="card"><h2>Jira por sprint y estado</h2><table><thead><tr><th>Sprint</th><th>Total</th><th>Finalizadas</th><th>Distribución</th></tr></thead><tbody>{"".join(sprint_rows)}</tbody></table></section>
<section class="card"><h2>Pull requests abiertas hacia dev</h2><ul>{pr_rows}</ul></section>
<section class="card"><h2>Últimas validaciones en dev</h2><table><thead><tr><th>Workflow</th><th>Estado</th><th>Resultado</th><th>Commit</th><th></th></tr></thead><tbody>{workflow_rows}</tbody></table></section>
<section class="card note"><strong>Importante:</strong> este informe no inventa un porcentaje de avance técnico. Las PR abiertas no cuentan como integradas; CI verde acredita validaciones ejecutadas, no aceptación funcional completa. El avance técnico requiere una rúbrica revisada con evidencias por sprint.</section>
</body></html>"""

def main() -> int:
    data = build()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "metrics.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "index.html").write_text(render_html(data), encoding="utf-8")
    done = data["jira"]["sprint_assigned_by_status"].get(DONE_STATUS, 0)
    total = data["jira"]["sprint_assigned"]
    pct = (done / total * 100) if total else 0
    summary = [
        "## EduGest · Métricas Jira + GitHub",
        f"- Corte: {data['generated_at']}",
        f"- Jira: {done}/{total} subtareas finalizadas en sprint ({pct:.1f}%).",
        f"- Subtareas sin sprint: {data['jira']['without_sprint']}.",
        f"- PR abiertas hacia dev: {data['github']['open_prs_to_dev']}.",
        "- Avance técnico: no calculado; requiere rúbrica y evidencias revisadas.",
        "",
        "### Workflows recientes en dev",
    ]
    summary += [f"- {w['name']}: {w['status']} / {w['conclusion']} ({w['sha']})" for w in data["github"]["latest_workflows_on_dev"]]
    (OUT / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("\n".join(summary))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Metrics generation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
