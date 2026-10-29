import ast
from pathlib import Path


def test_strict_modular_monolith_boundaries():
    """Verifies via AST analysis that no module app/modules/<A> imports app.modules.<B>.models."""
    root = Path(__file__).resolve().parent.parent
    modules_dir = root / "app" / "modules"
    assert modules_dir.exists() and modules_dir.is_dir(), (
        "app/modules directory must exist"
    )

    module_names = [
        d.name
        for d in modules_dir.iterdir()
        if d.is_dir() and not d.name.startswith("__")
    ]
    expected_modules = {
        "system",
        "inventory",
        "purchase",
        "mrp",
        "sales",
        "account",
        "hr",
        "bot",
    }
    assert expected_modules.issubset(set(module_names)), (
        f"Missing modules: {expected_modules - set(module_names)}"
    )

    violations = []

    for mod_name in module_names:
        mod_path = modules_dir / mod_name
        for py_file in mod_path.rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for other_mod in module_names:
                            if other_mod != mod_name and alias.name.startswith(
                                f"app.modules.{other_mod}.models"
                            ):
                                violations.append(
                                    f"{py_file.relative_to(root)} imports forbidden {alias.name}"
                                )
                elif isinstance(node, ast.ImportFrom) and node.module:
                    for other_mod in module_names:
                        if other_mod != mod_name:
                            if node.module == f"app.modules.{other_mod}.models":
                                violations.append(
                                    f"{py_file.relative_to(root)} imports from forbidden {node.module}"
                                )
                            elif node.module == f"app.modules.{other_mod}":
                                for alias in node.names:
                                    if alias.name == "models":
                                        violations.append(
                                            f"{py_file.relative_to(root)} imports models from {node.module}"
                                        )

    assert not violations, (
        "Modular Monolith Boundary Violations detected:\n" + "\n".join(violations)
    )
