#!/usr/bin/env python3
"""
check_compile.py — Verify that generated Python code compiles without errors.

Usage:
    echo '{"code": "def foo(): ..."}' | python check_compile.py

Output: JSON to stdout
    {"compile_ok": true/false, "error": ""}
"""

import sys
import json
import py_compile
import tempfile
import os


def check_compile(code: str) -> dict:
    """Check if code compiles successfully."""
    result = {"compile_ok": False, "error": ""}

    # Write code to temp file
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            tmp_path = f.name

        # Try to compile
        py_compile.compile(tmp_path, doraise=True)
        result["compile_ok"] = True

    except py_compile.PyCompileError as e:
        result["error"] = str(e)
    except SyntaxError as e:
        result["error"] = f"SyntaxError: {e.msg} (line {e.lineno})"
    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return result


def main():
    try:
        input_data = json.loads(sys.stdin.read())
        code = input_data["code"]
    except (json.JSONDecodeError, KeyError) as e:
        print(json.dumps({"compile_ok": False, "error": f"Invalid input: {e}"}))
        sys.exit(1)

    result = check_compile(code)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["compile_ok"] else 1)


if __name__ == "__main__":
    main()
