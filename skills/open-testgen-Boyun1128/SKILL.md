---
name: open-testgen-Boyun1128
description: Generate verified pytest test suites with mutation-based evaluation, then write result via scripts/run.py (file-based output contract).
version: 2.0.0
metadata:
  hermes:
    tags: [testing, pytest, mutation-testing, verification, aiase]
    category: testing
    requires_toolsets: [terminal]
---

# open-testgen-Boyun1128 (file-based output contract)

## When to Use
When the user sends `/open-testgen-Boyun1128 {json}` with `task_id`, `function_code`, `function_description`, `entry_function`, `examples`.

## Procedure

1. Read the input. Understand what the function does. Generate pytest test code that:
   - Tests normal cases (at least 2)
   - Tests boundary/edge cases (at least 2): empty input, single element, min/max
   - Tests error cases (at least 1)
   **CRITICAL: Do NOT define or import the tested function in your test code. The runner adds `from solution import <entry_function>` automatically. Just call the function directly in tests.**

2. Use the `terminal` tool to validate your tests against the reference:
```
echo '{"test_code": "<your test code>", "function_code": "<the function>", "entry_function": "<name>"}' | python3 <skill_dir>/scripts/run_tests.py
```
If tests fail on reference (reference_pass_rate < 1.0), fix tests and retry once.

3. Use the `terminal` tool to run mutation checking:
```
echo '{"test_code": "<your test code>", "function_code": "<the function>", "entry_function": "<name>"}' | python3 <skill_dir>/scripts/mutation_checker.py
```

4. **Use the `terminal` tool to write the final result (MANDATORY):**
```
python3 <skill_dir>/scripts/run.py --task_id "<task_id>" --test_code "<test_code>" --num_tests <N> --compile_ok "true" --reference_pass_rate <rate> --mutation_kill_rate <rate> --mutants_valid <N> --mutants_killed <N> --mutants_survived <N> --rationale "<reason>" --confidence 0.85
```

Replace `<skill_dir>` with the absolute path from `[Skill directory: ...]`.
After "written ok" appears, you are done.

**If you skip step 4, the evaluator gives 0 points regardless of test quality.**

## Pitfalls
- NEVER define or re-import the function being tested in test_code.
- Tests must pass on reference implementation.
- Tests must kill mutants (mutation_kill_rate >= 0.50).
- Do not write trivial tests (assert True).
- Use the terminal tool for all script calls.

## Verification
Task is complete ONLY after terminal tool runs scripts/run.py successfully (prints "written ok").
