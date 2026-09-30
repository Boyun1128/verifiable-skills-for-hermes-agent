#!/usr/bin/env python3
"""
check_imports.py — Verify that generated code does not use forbidden imports.

Usage:
    echo '{"code": "...", "imports_forbidden": ["os", "sys"]}' | python check_imports.py

Output: JSON to stdout
    {"imports_ok": true/false, "violations": [...]}
"""

import sys
import json
import ast


def check_imports(code: str, forbidden: list[str]) -> dict:
    """Check code for forbidden imports using AST analysis."""
    result = {"imports_ok": True, "violations": []}

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        result["imports_ok"] = False
        result["violations"].append(f"SyntaxError: cannot parse code: {e}")
        return result

    forbidden_set = set(forbidden)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_root = alias.name.split('.')[0]
                if module_root in forbidden_set:
                    result["imports_ok"] = False
                    result["violations"].append(
                        f"Forbidden import '{alias.name}' at line {node.lineno}"
                    )
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_root = node.module.split('.')[0]
                if module_root in forbidden_set:
                    result["imports_ok"] = False
                    result["violations"].append(
                        f"Forbidden 'from {node.module} import ...' at line {node.lineno}"
                    )

        # Check for dynamic imports
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == '__import__':
                result["imports_ok"] = False
                result["violations"].append(
                    f"Dynamic __import__() at line {node.lineno}"
                )
            elif isinstance(node.func, ast.Attribute):
                if (isinstance(node.func.value, ast.Name) and
                    node.func.value.id == 'importlib' and
                    node.func.attr == 'import_module'):
                    result["imports_ok"] = False
                    result["violations"].append(
                        f"Dynamic importlib.import_module() at line {node.lineno}"
                    )

    return result


def main():
    try:
        input_data = json.loads(sys.stdin.read())
        code = input_data["code"]
        forbidden = input_data.get("imports_forbidden", [])
    except (json.JSONDecodeError, KeyError) as e:
        print(json.dumps({"imports_ok": False, "violations": [f"Invalid input: {e}"]}))
        sys.exit(1)

    result = check_imports(code, forbidden)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["imports_ok"] else 1)


if __name__ == "__main__":
    main()
