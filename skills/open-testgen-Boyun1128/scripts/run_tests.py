#!/usr/bin/env python3
"""
run_tests.py — Execute generated pytest tests against reference implementation.

Usage:
    echo '{"test_code": "...", "function_code": "...", "entry_function": "..."}' | python run_tests.py

Validates:
1. Test code compiles (syntax check).
2. Tests can be collected by pytest.
3. All tests pass on the reference implementation.

Output: JSON to stdout
    {
        "compile_ok": true/false,
        "collect_ok": true/false,
        "reference_pass_rate": 1.0,
        "total_tests": 5,
        "passed": 5,
        "failed": 0,
        "errors": [],
        "error_details": ""
    }
"""

import sys
import json
import tempfile
import os
import subprocess
import shutil


def run_tests(test_code: str, function_code: str, entry_function: str) -> dict:
    """Run pytest tests against the reference implementation."""
    result = {
        "compile_ok": False,
        "collect_ok": False,
        "reference_pass_rate": 0.0,
        "total_tests": 0,
        "passed": 0,
        "failed": 0,
        "errors": [],
        "error_details": ""
    }

    # Create temp directory for test execution
    tmp_dir = tempfile.mkdtemp(prefix="testgen_")

    try:
        # Write function code
        func_path = os.path.join(tmp_dir, "solution.py")
        with open(func_path, 'w') as f:
            f.write(function_code)

        # Write test code with import of the function
        test_content = f"from solution import {entry_function}\n\n{test_code}"
        test_path = os.path.join(tmp_dir, "test_solution.py")
        with open(test_path, 'w') as f:
            f.write(test_content)

        # Step 1: Check if test code compiles
        compile_script = f'import py_compile, sys; py_compile.compile(sys.argv[1], doraise=True)'
        compile_result = subprocess.run(
            ['python', '-c', compile_script, test_path],
            capture_output=True, text=True, timeout=10,
            cwd=tmp_dir
        )

        if compile_result.returncode != 0:
            result["error_details"] = compile_result.stderr.strip()
            return result

        result["compile_ok"] = True

        # Step 2: Collect tests
        collect_result = subprocess.run(
            ['python', '-m', 'pytest', '--collect-only', '-q', test_path],
            capture_output=True, text=True, timeout=15,
            cwd=tmp_dir
        )

        if collect_result.returncode != 0 and 'no tests ran' not in collect_result.stdout:
            # Check if it's just warnings vs actual collection failure
            if 'ERROR' in collect_result.stdout or 'error' in collect_result.stderr.lower():
                result["error_details"] = collect_result.stdout + collect_result.stderr
                return result

        result["collect_ok"] = True

        # Count collected tests
        lines = collect_result.stdout.strip().split('\n')
        test_count = 0
        for line in lines:
            if '::test_' in line or line.strip().startswith('test_'):
                test_count += 1

        # Step 3: Run tests
        run_result = subprocess.run(
            ['python', '-m', 'pytest', test_path, '-v', '--tb=short', '--no-header'],
            capture_output=True, text=True, timeout=30,
            cwd=tmp_dir
        )

        # Parse pytest output
        output_lines = run_result.stdout.strip().split('\n')
        passed = 0
        failed = 0
        errors = []

        for line in output_lines:
            if ' PASSED' in line:
                passed += 1
            elif ' FAILED' in line:
                failed += 1
                errors.append(line.strip())
            elif ' ERROR' in line:
                failed += 1
                errors.append(line.strip())

        total = passed + failed
        if total == 0:
            total = test_count if test_count > 0 else 1

        result["total_tests"] = total
        result["passed"] = passed
        result["failed"] = failed
        result["errors"] = errors
        result["reference_pass_rate"] = passed / total if total > 0 else 0.0
        result["error_details"] = run_result.stderr.strip() if failed > 0 else ""

    except subprocess.TimeoutExpired:
        result["error_details"] = "Test execution timed out"
    except Exception as e:
        result["error_details"] = f"Unexpected error: {str(e)}"
    finally:
        # Cleanup
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return result


def main():
    try:
        input_data = json.loads(sys.stdin.read())
        test_code = input_data["test_code"]
        function_code = input_data["function_code"]
        entry_function = input_data.get("entry_function", "")

        # Auto-detect entry function if not provided
        if not entry_function:
            import ast
            try:
                tree = ast.parse(function_code)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
                        entry_function = node.name
                        break
            except SyntaxError:
                pass

    except (json.JSONDecodeError, KeyError) as e:
        print(json.dumps({
            "compile_ok": False, "collect_ok": False,
            "reference_pass_rate": 0.0, "total_tests": 0,
            "passed": 0, "failed": 0, "errors": [str(e)],
            "error_details": f"Input error: {e}"
        }))
        sys.exit(1)

    result = run_tests(test_code, function_code, entry_function)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["reference_pass_rate"] == 1.0 else 1)


if __name__ == "__main__":
    main()
