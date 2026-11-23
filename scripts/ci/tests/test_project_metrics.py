import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "project-metrics" / "build_metrics.py"

os.environ.setdefault("JIRA_BASE_URL", "https://example.atlassian.net")
os.environ.setdefault("JIRA_EMAIL", "metrics@example.invalid")
os.environ.setdefault("JIRA_API_TOKEN", "test-token")
os.environ.setdefault("GITHUB_TOKEN", "test-token")

spec = importlib.util.spec_from_file_location("project_metrics_builder", MODULE_PATH)
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)


def issue(key, status, labels):
    return {
        "key": key,
        "fields": {
            "summary": key,
            "status": {"name": status},
            "labels": labels,
        },
    }


class ProjectMetricsTests(unittest.TestCase):
    @patch.object(metrics, "github_get")
    @patch.object(metrics, "jira_issues")
    def test_unassigned_completed_tasks_do_not_inflate_sprint_rate(self, jira, github):
        jira.return_value = [
            issue("KAN-1", "Finalizada", ["pf2-v41", "v41-s0"]),
            issue("KAN-2", "Idea", ["pf2-v41", "v41-s1"]),
            issue("KAN-3", "Finalizada", ["pf2-v41"]),
        ]
        github.side_effect = [
            [],
            {"workflow_runs": []},
        ]

        snapshot = metrics.build()

        self.assertEqual(snapshot["jira"]["total"], 3)
        self.assertEqual(snapshot["jira"]["sprint_assigned"], 2)
        self.assertEqual(snapshot["jira"]["without_sprint"], 1)
        self.assertEqual(snapshot["jira"]["by_status"]["Finalizada"], 2)
        self.assertEqual(snapshot["jira"]["sprint_assigned_by_status"]["Finalizada"], 1)
        html = metrics.render_html(snapshot)
        self.assertIn("1/2", html)
        self.assertIn("50.0%", html)

    @patch.object(metrics, "github_get")
    @patch.object(metrics, "jira_issues")
    def test_sprint_breakdown_and_open_prs_are_reported(self, jira, github):
        jira.return_value = [
            issue("KAN-4", "Finalizada", ["pf2-v41", "v41-s0"]),
            issue("KAN-5", "Pruebas", ["pf2-v41", "v41-s0"]),
        ]
        github.side_effect = [
            [{"number": 12, "title": "Feature", "html_url": "https://github.com/example/repo/pull/12",
              "head": {"ref": "feature/demo"}, "updated_at": "2026-11-23T10:00:00Z"}],
            {"workflow_runs": [{"name": "CI", "status": "completed", "conclusion": "success",
                                "updated_at": "2026-11-23T10:00:00Z", "html_url": "https://github.com/example/repo/actions/runs/1",
                                "head_sha": "1234567890"}]},
        ]

        snapshot = metrics.build()

        self.assertEqual(snapshot["jira"]["sprints"]["v41-s0"]["total"], 2)
        self.assertEqual(snapshot["github"]["open_prs_to_dev"], 1)
        self.assertEqual(snapshot["github"]["pull_requests"][0]["number"], 12)
        self.assertEqual(snapshot["github"]["latest_workflows_on_dev"][0]["conclusion"], "success")


if __name__ == "__main__":
    unittest.main()
