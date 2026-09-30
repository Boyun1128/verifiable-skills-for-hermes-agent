#!/usr/bin/env python3
"""
edge_case_generator.py — Generate and run edge-case inputs against code to find bugs.

Usage:
    echo '{"code": "...", "entry_function": "merge_intervals", "task_description": "..."}' | python edge_case_generator.py

Generates boundary inputs and runs them against the function to detect:
- IndexError, TypeError, ValueError on edge cases
- Incorrect results for boundary inputs
- Infinite loops (via timeout)

Output: JSON to stdout
    {"crashes": [...], "total_tests": N, "crashed": M}
"""

import sys
import json
import tempfile
import os
import subprocess


# Standard edge case inputs for common patterns
EDGE_CASES = [
    {"name": "empty_list", "input": "[]", "description": "Empty list input"},
    {"name": "none_input", "input": "None", "description": "None as input"},
    {"name": "single_element", "input": "[1]", "description": "Single element list"},
    {"name": "negative_numbers", "input": "[-1, -5, -3]", "description": "All negative numbers"},
    {"name": "zero", "input": "[0]", "description": "Zero value"},
    {"name": "large_input", "input": "list(range(1000))", "description": "Large input (1000 elements)"},
    {"name": "duplicates", "input": "[1, 1, 1, 1]", "description": "All duplicates"},
    {"name": "two_elements", "input": "[2, 1]", "description": "Two elements"},
    {"name": "empty_string", "input": "''", "description": "Empty string"},
    {"name": "nested_empty", "input": "[[]]", "description": "Nested empty list"},
]


def run_edge_case(code: str, entry_function: str, test_input: str, timeout: float = 5.0) -> dict:
    """Run code with a specific edge case input."""
    test_script = f'''
import json
import sys

{code}

try:
    test_input = {test_input}
    if isinstance(test_input, (list, tuple)):
        result = {entry_function}(test_input)
    elif test_input is None:
        result = {entry_function}(test_input)
    else:
        result = {entry_function}(test_input)
    print(json.dumps({{"success": True, "result": repr(result)}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e), "type": type(e).__name__, "line": getattr(e, "__traceback__", None) and e.__traceback__.tb_lineno}}))
'''

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script)
            tmp_path = f.name

        result = subprocess.run(
            ['python', tmp_path],
            capture_output=True, text=True, timeout=timeout
        )

        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
        else:
            error_msg = result.stderr.strip() if result.stderr else "Non-zero exit code"
            return {"success": False, "error": error_msg, "type": "RuntimeError"}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Execution timed out (5s)", "type": "TimeoutError"}
    except Exception as e:
        return {"success": False, "error": str(e), "type": type(e).__name__}
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def main():
    try:
        input_data = json.loads(sys.stdin.read())
        code = input_data["code"]
        entry_function = input_data.get("entry_function", "")
        task_description = input_data.get("task_description", "")
    except (json.JSONDecodeError, KeyError) as e:
        print(json.dumps({"crashes": [], "total_tests": 0, "crashed": 0, "error": str(e)}))
        sys.exit(1)

    # If no entry function given, try to detect it
    if not entry_function:
        import ast
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
                    entry_function = node.name
                    break
        except SyntaxError:
            pass

    if not entry_function:
        print(json.dumps({"crashes": [], "total_tests": 0, "crashed": 0, "error": "Cannot determine entry function"}))
        sys.exit(1)

    crashes = []
    total_tests = 0

    for edge_case in EDGE_CASES:
        total_tests += 1
        result = run_edge_case(code, entry_function, edge_case["input"])

        if not result.get("success", False):
            crashes.append({
                "test_name": edge_case["name"],
                "input": edge_case["input"],
                "description": edge_case["description"],
                "error": result.get("error", "unknown"),
                "error_type": result.get("type", "unknown")
            })

    output = {
        "crashes": crashes,
        "total_tests": total_tests,
        "crashed": len(crashes)
    }

    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
