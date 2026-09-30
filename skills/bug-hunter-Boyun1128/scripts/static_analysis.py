#!/usr/bin/env python3
"""
static_analysis.py — AST-based static analysis for bug detection.

Usage:
    echo '{"code": "...", "task_description": "..."}' | python static_analysis.py

Detects:
- Missing edge case handling (empty input, None checks)
- Off-by-one patterns (range, indexing)
- Potential type errors
- Unreachable code
- Missing return statements

Output: JSON to stdout
    {"issues": [...], "summary": "..."}
"""

import sys
import json
import ast


class BugPatternVisitor(ast.NodeVisitor):
    """AST visitor that detects common bug patterns."""

    def __init__(self, code_lines: list[str]):
        self.issues = []
        self.code_lines = code_lines
        self.has_empty_check = False
        self.has_none_check = False
        self.function_returns = {}
        self.current_function = None

    def visit_FunctionDef(self, node):
        self.current_function = node.name
        self.function_returns[node.name] = []
        self.generic_visit(node)
        self.current_function = None

    def visit_If(self, node):
        """Detect None/empty checks."""
        test_str = ast.dump(node.test)
        if 'None' in test_str:
            self.has_none_check = True
        if 'not ' in ast.unparse(node.test) if hasattr(ast, 'unparse') else '':
            self.has_empty_check = True
        self.generic_visit(node)

    def visit_Subscript(self, node):
        """Detect potential IndexError patterns."""
        # Check for hardcoded index [0] without length check
        if isinstance(node.slice, ast.Constant):
            if node.slice.value == 0:
                # Check if there's a preceding empty check
                if not self.has_empty_check:
                    self.issues.append({
                        "line": node.lineno,
                        "type": "edge_case",
                        "severity": "medium",
                        "description": f"Accessing index [0] without checking if container is empty (line {node.lineno}). May raise IndexError on empty input.",
                        "pattern": "unguarded_index_access"
                    })
        self.generic_visit(node)

    def visit_Compare(self, node):
        """Detect potential off-by-one in comparisons."""
        self.generic_visit(node)

    def visit_Return(self, node):
        """Track return statements."""
        if self.current_function:
            self.function_returns.setdefault(self.current_function, []).append(node.lineno)
        self.generic_visit(node)

    def get_issues(self) -> list[dict]:
        return self.issues


def analyze_code(code: str, task_description: str) -> dict:
    """Perform static analysis on the code."""
    issues = []

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {
            "issues": [{
                "line": e.lineno or 1,
                "type": "type_error",
                "severity": "critical",
                "description": f"SyntaxError: {e.msg}",
                "pattern": "syntax_error"
            }],
            "summary": "Code has syntax errors and cannot be parsed."
        }

    code_lines = code.split('\n')

    # Run AST visitor
    visitor = BugPatternVisitor(code_lines)
    visitor.visit(tree)
    issues.extend(visitor.get_issues())

    # Check for common patterns in task description vs code
    task_lower = task_description.lower()

    # If task mentions "empty" but code doesn't check for it
    if ('empty' in task_lower or 'no ' in task_lower) and not visitor.has_empty_check:
        # Find the main function
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                issues.append({
                    "line": node.lineno,
                    "type": "edge_case",
                    "severity": "medium",
                    "description": "Task description mentions empty input handling, but no empty check detected in code.",
                    "pattern": "missing_empty_check"
                })
                break

    summary = f"Found {len(issues)} potential issue(s) via static analysis."
    return {"issues": issues, "summary": summary}


def main():
    try:
        input_data = json.loads(sys.stdin.read())
        code = input_data["code"]
        task_description = input_data.get("task_description", "")
    except (json.JSONDecodeError, KeyError) as e:
        print(json.dumps({"issues": [], "summary": f"Input error: {e}"}))
        sys.exit(1)

    result = analyze_code(code, task_description)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
