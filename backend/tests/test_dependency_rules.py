"""
PLAN.md §1.1's app-layout rule, enforced automatically:

    accounts  <-  holdings  <-  targets  <-  layouts
    marketdata <- holdings

i.e. accounts and marketdata must import from nothing else in the project;
holdings may import accounts/marketdata; targets may import holdings;
layouts may import everything.

`accounts` and `holdings` exist so far (holdings may import accounts, and
does - Profile.Currency); the rest are covered automatically as they're
added in later steps, rather than needing a rewrite each time.
"""

import ast
from pathlib import Path

from django.test import SimpleTestCase

BASE_DIR = Path(__file__).resolve().parent.parent

# app -> apps it is NOT allowed to import from, per the dependency graph.
FORBIDDEN = {
    "accounts": {"holdings", "targets", "layouts", "marketdata"},
    "marketdata": {"accounts", "holdings", "targets", "layouts"},
    "holdings": {"targets", "layouts"},
    "targets": {"layouts"},
}

PROJECT_APPS = {"accounts", "holdings", "targets", "layouts", "marketdata"}


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
    def test_apps_only_import_whats_allowed(self):
        violations = []
        for app_name, forbidden_apps in FORBIDDEN.items():
            app_dir = BASE_DIR / app_name
            if not app_dir.is_dir():
                continue  # app not built yet
            for py_file in app_dir.rglob("*.py"):
                if "migrations" in py_file.parts:
                    continue
                imported = _imported_top_level_modules(py_file) & PROJECT_APPS
                bad = imported & forbidden_apps
                if bad:
                    violations.append(f"{py_file.relative_to(BASE_DIR)} imports {sorted(bad)}")

        self.assertEqual(violations, [], "Dependency rule violations:\n" + "\n".join(violations))
