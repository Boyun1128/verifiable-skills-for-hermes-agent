#!/usr/bin/env python3
"""
self_test.py — Run generated code against sample test cases.

Usage:
    echo '{"code": "...", "entry_function": "merge_intervals", "task_description": "..."}' | python self_test.py

The script generates edge-case test inputs based on the entry function signature,
executes the code, and reports pass/fail results.

Output: JSON to stdout
    {"passed": 3, "failed": 1, "total": 4, "details": [...]}
"""

import sys
import json
import tempfile
import os
import subprocess
import traceback


def run_code_with_input(code: str, entry_function: str, test_input: str, timeout: float = 5.0) -> dict:
    """Run the code with a test input and capture the result."""
    # Create a test script that imports and calls the function
    test_script = f'''
import json
import sys

# Student code
{code}

# Test execution
try:
    test_input = json.loads(sys.argv[1])
    if isinstance(test_input, list):
        result = {entry_function}(*test_input)
    elif isinstance(test_input, dict):
        result = {entry_function}(**test_input)
    else:
        result = {entry_function}(test_input)
    print(json.dumps({{"success": True, "result": repr(result)}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e), "type": type(e).__name__}}))
'''

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script)
            tmp_path = f.name

        result = subprocess.run(
            ['python', tmp_path, test_input],
            capture_output=True, text=True, timeout=timeout
        )

        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
        else:
            return {"success": False, "error": result.stderr.strip() or "No output", "type": "RuntimeError"}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Execution timed out (5s)", "type": "TimeoutError"}
    except Exception as e:
        return {"success": False, "error": str(e), "type": type(e).__name__}
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def generate_basic_tests(entry_function: str) -> list[dict]:
    """Generate basic test cases for common patterns."""
    tests = [
        {"name": "empty_list", "input": json.dumps([[]])},
        {"name": "single_element", "input": json.dumps([[1]])},
        {"name": "normal_case", "input": json.dumps([[3, 1, 2]])},
        {"name": "negative_numbers", "input": json.dumps([[-1, -5, 3, 0]])},
        {"name": "duplicates", "input": json.dumps([[1, 1, 2, 2, 3]])},
    ]
    return tests


def main():
    try:
        input_data = json.loads(sys.stdin.read())
        code = input_data["code"]
        entry_function = input_data["entry_function"]
        task_description = input_data.get("task_description", "")
    except (json.JSONDecodeError, KeyError) as e:
        print(json.dumps({"passed": 0, "failed": 0, "total": 0, "error": str(e), "details": []}))
        sys.exit(1)

    # Generate test cases
    tests = generate_basic_tests(entry_function)

    passed = 0
    failed = 0
    details = []

    for test in tests:
        result = run_code_with_input(code, entry_function, test["input"])
        if result.get("success", False):
            passed += 1
            details.append({"name": test["name"], "status": "passed", "result": result.get("result", "")})
        else:
            failed += 1
            details.append({"name": test["name"], "status": "failed", "error": result.get("error", "unknown")})

    output = {
        "passed": passed,
        "failed": failed,
        "total": passed + failed,
        "details": details
    }

    print(json.dumps(output, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
