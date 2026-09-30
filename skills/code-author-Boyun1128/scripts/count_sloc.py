#!/usr/bin/env python3
"""
count_sloc.py — Count Source Lines of Code using radon raw (or fallback to manual count).

Usage:
    echo '{"code": "..."}' | python count_sloc.py

Output: JSON to stdout
    {"sloc": 9, "within_limit": true, "max_loc": 500}
"""

import sys
import json
import tempfile
import os
import subprocess


def count_sloc_radon(code: str) -> int:
    """Count SLOC using radon raw --json."""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            tmp_path = f.name

        result = subprocess.run(
            ['python', '-m', 'radon', 'raw', '--json', tmp_path],
            capture_output=True, text=True, timeout=10
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            # radon output: {filepath: {sloc: N, ...}}
            for filepath, metrics in data.items():
                return metrics.get('sloc', 0)

    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        pass
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    # Fallback: manual count
    return count_sloc_manual(code)


def count_sloc_manual(code: str) -> int:
    """Manual SLOC count: non-empty, non-comment lines."""
    count = 0
    in_docstring = False
    lines = code.split('\n')

    for line in lines:
        stripped = line.strip()

        # Handle docstrings
        if '"""' in stripped or "'''" in stripped:
            quote = '"""' if '"""' in stripped else "'''"
            occurrences = stripped.count(quote)
            if occurrences >= 2:
                # Single-line docstring
                continue
            else:
                in_docstring = not in_docstring
                continue

        if in_docstring:
            continue

        # Skip empty lines and pure comment lines
        if stripped == '' or stripped.startswith('#'):
            continue

        count += 1

    return count


def main():
    try:
        input_data = json.loads(sys.stdin.read())
        code = input_data["code"]
        max_loc = input_data.get("max_loc", 500)
    except (json.JSONDecodeError, KeyError) as e:
        print(json.dumps({"sloc": -1, "within_limit": False, "max_loc": 500, "error": str(e)}))
        sys.exit(1)

    sloc = count_sloc_radon(code)
    within_limit = sloc <= max_loc

    result = {
        "sloc": sloc,
        "within_limit": within_limit,
        "max_loc": max_loc
    }

    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if within_limit else 1)


if __name__ == "__main__":
    main()
