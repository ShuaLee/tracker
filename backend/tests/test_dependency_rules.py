"""
PLAN.md section 3's dependency direction, enforced:

    users <- portfolios <- assets <- tags <- targets <- sheets
    history and imports sit beside assets; marketdata is used by assets.
    Nothing imports sheets.

Each project app may import only the apps "upstream" of it. Apps that don't
exist yet are skipped, so this covers each one automatically as it's built.
"""

import ast
from pathlib import Path

from django.test import SimpleTestCase

BASE_DIR = Path(__file__).resolve().parent.parent

# app -> project apps it may import.
ALLOWED = {
    "users": set(),
    "marketdata": set(),
    "portfolios": {"users"},
    "assets": {"users", "portfolios", "marketdata"},
    "history": {"users", "portfolios", "assets", "marketdata"},
    "imports": {"users", "portfolios", "assets", "marketdata"},
    "tags": {"users", "portfolios", "assets"},
    "targets": {"users", "portfolios", "assets", "tags"},
    "sheets": {"users", "portfolios", "assets", "tags", "targets", "history", "marketdata"},
}
PROJECT_APPS = set(ALLOWED)


def _imported_top_level_modules(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module.split(".")[0])
    return modules


class DependencyRuleTests(SimpleTestCase):
    def test_apps_only_import_upstream_apps(self):
        violations = []
        for app, allowed in ALLOWED.items():
            app_dir = BASE_DIR / app
            if not app_dir.is_dir():
                continue  # not built yet
            for py_file in app_dir.rglob("*.py"):
                if "migrations" in py_file.parts:
                    continue
                bad = (_imported_top_level_modules(py_file) & PROJECT_APPS) - allowed - {app}
                if bad:
                    violations.append(f"{py_file.relative_to(BASE_DIR)} imports {sorted(bad)}")
        self.assertEqual(violations, [], "Dependency rule violations:\n" + "\n".join(violations))

    def test_every_built_project_app_is_covered(self):
        # A new top-level app must be added to ALLOWED, or it would escape the rule.
        ignored = {"config", "tests", ".venv"}
        built = {
            p.name for p in BASE_DIR.iterdir()
            if p.is_dir() and (p / "apps.py").exists() and p.name not in ignored
        }
        self.assertEqual(built - PROJECT_APPS, set(), "Add new apps to ALLOWED in this test.")
