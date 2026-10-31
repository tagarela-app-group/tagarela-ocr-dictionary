import ast
from collections.abc import Iterator
from importlib import import_module
from pathlib import Path

from django.test import SimpleTestCase

from apps.common.serializers import StrictSerializer

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


def input_serializers(source: str) -> set[str]:
    return {
        node.func.id
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and any(keyword.arg == "data" for keyword in node.keywords)
    }


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

    def test_every_view_input_goes_through_a_strict_serializer(self) -> None:
        lax: list[str] = []
        inputs = 0
        for path in APPS_DIR.glob("*/views.py"):
            module = import_module(f"apps.{path.parent.name}.views")
            for name in input_serializers(path.read_text(encoding="utf-8")):
                inputs += 1
                if not issubclass(getattr(module, name), StrictSerializer):
                    lax.append(f"{path.parent.name}: {name}")

        self.assertEqual(lax, [])
        self.assertGreater(inputs, 0)

    def test_input_serializers_only_reads_calls_with_data(self) -> None:
        source = "A(data=x)\nB(capture, data=x, partial=True)\nC(capture)\nResponse(D(y).data)\n"

        self.assertEqual(input_serializers(source), {"A", "B"})
