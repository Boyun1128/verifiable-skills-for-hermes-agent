#!/usr/bin/env python3
"""
mutation_checker.py — AST-level mutation testing for generated test suites.

Usage:
    echo '{"test_code": "...", "function_code": "...", "entry_function": "..."}' | python mutation_checker.py

Generates mutants of the function by:
1. Boundary/Compare mutations: > ↔ >=, < ↔ <=, == ↔ !=
2. Condition negation: if cond → if not cond
3. Return mutations: return x → return None

Then runs the test suite against each mutant to compute mutation kill rate.

Output: JSON to stdout
    {
        "mutants_total": 12,
        "mutants_valid": 9,
        "mutants_killed": 6,
        "mutants_survived": 3,
        "mutants_excluded": {"invalid": 1, "suspected_equivalent": 2},
        "mutation_kill_rate": 0.67,
        "mutation_details": [...]
    }
"""

import sys
import json
import ast
import copy
import tempfile
import os
import subprocess
import shutil


# ============================================================
# Mutation Operators
# ============================================================

class ComparisonMutator(ast.NodeTransformer):
    """Mutate comparison operators: > ↔ >=, < ↔ <=, == ↔ !="""

    MUTATIONS = {
        ast.Gt: ast.GtE,
        ast.GtE: ast.Gt,
        ast.Lt: ast.LtE,
        ast.LtE: ast.Lt,
        ast.Eq: ast.NotEq,
        ast.NotEq: ast.Eq,
    }

    def __init__(self, target_index: int):
        self.current_index = 0
        self.target_index = target_index
        self.mutated = False

    def visit_Compare(self, node):
        new_ops = []
        for op in node.ops:
            if self.current_index == self.target_index and not self.mutated:
                new_op_type = self.MUTATIONS.get(type(op))
                if new_op_type:
                    new_ops.append(new_op_type())
                    self.mutated = True
                else:
                    new_ops.append(op)
            else:
                new_ops.append(op)
            self.current_index += 1

        node.ops = new_ops
        return node


class ConditionNegator(ast.NodeTransformer):
    """Negate if conditions: if cond → if not cond"""

    def __init__(self, target_index: int):
        self.current_index = 0
        self.target_index = target_index
        self.mutated = False

    def visit_If(self, node):
        if self.current_index == self.target_index and not self.mutated:
            node.test = ast.UnaryOp(op=ast.Not(), operand=node.test)
            self.mutated = True
        self.current_index += 1
        self.generic_visit(node)
        return node


class ReturnMutator(ast.NodeTransformer):
    """Mutate return statements: return x → return None"""

    def __init__(self, target_index: int):
        self.current_index = 0
        self.target_index = target_index
        self.mutated = False

    def visit_Return(self, node):
        if self.current_index == self.target_index and not self.mutated:
            if node.value is not None:
                node.value = ast.Constant(value=None)
                self.mutated = True
        self.current_index += 1
        return node


# ============================================================
# Mutation Generation
# ============================================================

def count_comparison_ops(tree) -> int:
    """Count comparison operators in the AST."""
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            count += len(node.ops)
    return count


def count_if_statements(tree) -> int:
    """Count if statements in the AST."""
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            count += 1
    return count


def count_return_statements(tree) -> int:
    """Count return statements with values in the AST."""
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and node.value is not None:
            count += 1
    return count


def generate_mutants(function_code: str) -> list[dict]:
    """Generate all possible mutants from the function code."""
    mutants = []

    try:
        tree = ast.parse(function_code)
    except SyntaxError:
        return mutants

    # Comparison mutations
    num_comparisons = count_comparison_ops(tree)
    for i in range(num_comparisons):
        try:
            mutant_tree = copy.deepcopy(tree)
            mutator = ComparisonMutator(target_index=i)
            mutator.visit(mutant_tree)
            if mutator.mutated:
                ast.fix_missing_locations(mutant_tree)
                mutant_code = ast.unparse(mutant_tree)
                mutants.append({
                    "type": "comparison",
                    "index": i,
                    "code": mutant_code
                })
        except Exception:
            continue

    # Condition negation mutations
    num_ifs = count_if_statements(tree)
    for i in range(num_ifs):
        try:
            mutant_tree = copy.deepcopy(tree)
            mutator = ConditionNegator(target_index=i)
            mutator.visit(mutant_tree)
            if mutator.mutated:
                ast.fix_missing_locations(mutant_tree)
                mutant_code = ast.unparse(mutant_tree)
                mutants.append({
                    "type": "condition_negation",
                    "index": i,
                    "code": mutant_code
                })
        except Exception:
            continue

    # Return mutations
    num_returns = count_return_statements(tree)
    for i in range(num_returns):
        try:
            mutant_tree = copy.deepcopy(tree)
            mutator = ReturnMutator(target_index=i)
            mutator.visit(mutant_tree)
            if mutator.mutated:
                ast.fix_missing_locations(mutant_tree)
                mutant_code = ast.unparse(mutant_tree)
                mutants.append({
                    "type": "return_mutation",
                    "index": i,
                    "code": mutant_code
                })
        except Exception:
            continue

    return mutants


def is_equivalent_mutant(original_code: str, mutant_code: str, entry_function: str) -> bool:
    """Check if a mutant is likely equivalent by running probe inputs."""
    # Use a diverse set of probe inputs that work for various function signatures
    # These cover: int, list, str, tuple, and edge cases
    probe_inputs = [
        "0", "1", "2", "5", "10", "-1",
        "[]", "[1]", "[1, 2, 3]", "[0, 0]", "[-1, 0, 1]",
        "''", "'a'", "'abc'", "'aba'",
        "None",
    ]

    tmp_dir = tempfile.mkdtemp(prefix="equiv_check_")
    any_difference = False
    any_valid_probe = False

    try:
        for probe in probe_inputs:
            # Run original
            orig_script = f"{original_code}\n\ntry:\n    result = {entry_function}({probe})\n    print(repr(result))\nexcept Exception as e:\n    print(f'EXCEPTION:{{type(e).__name__}}')\n"
            mut_script = f"{mutant_code}\n\ntry:\n    result = {entry_function}({probe})\n    print(repr(result))\nexcept Exception as e:\n    print(f'EXCEPTION:{{type(e).__name__}}')\n"

            orig_path = os.path.join(tmp_dir, "orig.py")
            mut_path = os.path.join(tmp_dir, "mut.py")

            with open(orig_path, 'w') as f:
                f.write(orig_script)
            with open(mut_path, 'w') as f:
                f.write(mut_script)

            try:
                orig_result = subprocess.run(
                    ['python', orig_path], capture_output=True, text=True, timeout=5
                )
                mut_result = subprocess.run(
                    ['python', mut_path], capture_output=True, text=True, timeout=5
                )

                orig_out = orig_result.stdout.strip()
                mut_out = mut_result.stdout.strip()

                # Skip probes where original throws exception (wrong input type)
                if orig_out.startswith('EXCEPTION:'):
                    continue

                any_valid_probe = True

                if orig_out != mut_out:
                    any_difference = True
                    return False  # Different output = not equivalent

            except subprocess.TimeoutExpired:
                # Timeout on mutant but not original = not equivalent
                any_difference = True
                return False

        # If no valid probe worked, assume NOT equivalent (be conservative)
        if not any_valid_probe:
            return False

        # All valid probes gave same output = likely equivalent
        return not any_difference

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def run_tests_against_mutant(test_code: str, mutant_code: str, entry_function: str) -> bool:
    """Run test suite against a mutant. Returns True if tests KILL the mutant (at least one fails)."""
    tmp_dir = tempfile.mkdtemp(prefix="mutant_test_")

    try:
        # Write mutant as solution.py
        func_path = os.path.join(tmp_dir, "solution.py")
        with open(func_path, 'w') as f:
            f.write(mutant_code)

        # Write test file
        test_content = f"from solution import {entry_function}\n\n{test_code}"
        test_path = os.path.join(tmp_dir, "test_solution.py")
        with open(test_path, 'w') as f:
            f.write(test_content)

        # Run pytest
        result = subprocess.run(
            ['python', '-m', 'pytest', test_path, '-x', '--tb=no', '-q'],
            capture_output=True, text=True, timeout=15,
            cwd=tmp_dir
        )

        # If pytest returns non-zero, tests failed = mutant killed
        return result.returncode != 0

    except subprocess.TimeoutExpired:
        # Timeout = mutant likely caused infinite loop = killed
        return True
    except Exception:
        return False
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ============================================================
# Main
# ============================================================

def main():
    try:
        input_data = json.loads(sys.stdin.read())
        test_code = input_data["test_code"]
        function_code = input_data["function_code"]
        entry_function = input_data.get("entry_function", "")

        # Auto-detect entry function
        if not entry_function:
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
            "mutants_total": 0, "mutants_valid": 0,
            "mutants_killed": 0, "mutants_survived": 0,
            "mutants_excluded": {"invalid": 0, "suspected_equivalent": 0},
            "mutation_kill_rate": 0.0, "mutation_details": [],
            "error": str(e)
        }))
        sys.exit(1)

    # Generate mutants
    mutants = generate_mutants(function_code)

    mutants_total = len(mutants)
    mutants_valid = 0
    mutants_killed = 0
    mutants_survived = 0
    invalid_count = 0
    equivalent_count = 0
    mutation_details = []

    for mutant in mutants:
        mutant_code = mutant["code"]

        # Check if mutant compiles
        try:
            compile(mutant_code, "<mutant>", "exec")
        except SyntaxError:
            invalid_count += 1
            mutation_details.append({
                "type": mutant["type"],
                "index": mutant["index"],
                "status": "invalid",
                "reason": "compile_error"
            })
            continue

        # Check if equivalent
        if is_equivalent_mutant(function_code, mutant_code, entry_function):
            equivalent_count += 1
            mutation_details.append({
                "type": mutant["type"],
                "index": mutant["index"],
                "status": "excluded",
                "reason": "suspected_equivalent"
            })
            continue

        mutants_valid += 1

        # Run tests against mutant
        killed = run_tests_against_mutant(test_code, mutant_code, entry_function)

        if killed:
            mutants_killed += 1
            mutation_details.append({
                "type": mutant["type"],
                "index": mutant["index"],
                "status": "killed"
            })
        else:
            mutants_survived += 1
            mutation_details.append({
                "type": mutant["type"],
                "index": mutant["index"],
                "status": "survived"
            })

    # Calculate kill rate (only count valid, non-equivalent mutants)
    kill_rate = mutants_killed / mutants_valid if mutants_valid > 0 else 0.0

    output = {
        "mutants_total": mutants_total,
        "mutants_valid": mutants_valid,
        "mutants_killed": mutants_killed,
        "mutants_survived": mutants_survived,
        "mutants_excluded": {
            "invalid": invalid_count,
            "suspected_equivalent": equivalent_count
        },
        "mutation_kill_rate": round(kill_rate, 4),
        "mutation_details": mutation_details
    }

    print(json.dumps(output, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
