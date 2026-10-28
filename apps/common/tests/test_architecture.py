import ast
from collections.abc import Iterator
from pathlib import Path

from django.test import SimpleTestCase

APPS_DIR = Path(__file__).resolve().parents[2]

LAYERS: dict[str, int] = {
    "common": 0,
    "accounts": 1,
    "courses": 1,
    "language_analysis": 1,
    "vocabulary": 2,
    "captures": 3,
    "cards": 4,
    "exercises": 5,
    "reviews": 6,
}


def imported_apps(source: str) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    return {module.split(".")[1] for module in modules if module.startswith("apps.")}


def production_files(app: str) -> Iterator[Path]:
    for path in (APPS_DIR / app).rglob("*.py"):
        if not {"tests", "migrations"} & set(path.parts):
            yield path


class ArchitectureTests(SimpleTestCase):
    def test_every_app_has_a_layer(self):
        apps = {path.parent.name for path in APPS_DIR.glob("*/__init__.py")}

        self.assertEqual(apps, set(LAYERS))

    def test_dependencies_only_go_down(self):
        upward = [
            f"{path.relative_to(APPS_DIR)}: {app} -> {target}"
            for app, layer in LAYERS.items()
            for path in production_files(app)
            for target in imported_apps(path.read_text(encoding="utf-8")) - {app}
            if LAYERS[target] >= layer
        ]

        self.assertEqual(upward, [])

    def test_imported_apps_reads_both_import_forms(self):
        source = "import apps.courses.models\nfrom apps.vocabulary.models import Term\nimport os\n"

        self.assertEqual(imported_apps(source), {"courses", "vocabulary"})
