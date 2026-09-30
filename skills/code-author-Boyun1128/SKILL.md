---
name: code-author-Boyun1128
description: Generate verified Python code from task descriptions, then write result via scripts/run.py (file-based output contract).
version: 2.0.0
metadata:
  hermes:
    tags: [code, python, generation, testing, aiase]
    category: code
    requires_toolsets: [terminal]
---

# code-author-Boyun1128 (file-based output contract)

## When to Use
When the user sends `/code-author-Boyun1128 {json}` with `task_id`, `task_description`, `constraints`.

## Procedure
This task has exactly ONE required action: run `scripts/run.py` via the `terminal` tool.
The result is graded ONLY from the file that script writes. Your chat text is ignored.

Step 1. Read the task. Write Python code with the exact `entry_function` name. Handle edge cases (empty, None, single, negative, duplicates). Avoid forbidden imports. Keep under 500 SLOC.
Step 2. Use the `terminal` tool to run scripts/run.py with your code. This is the ONLY way to finish.

### Worked Example
Input: `{"task_id":"ex1","task_description":"add(a,b): return a+b","constraints":{"entry_function":"add","max_loc":500,"imports_forbidden":["os"]}}`

Your terminal command (the ENTIRE response — just the tool call):
```
python3 <skill_dir>/scripts/run.py --task_id "ex1" --code "def add(a, b):
    return a + b" --loc 2 --self_test_passed 1 --self_test_failed 0 --rationale "Simple addition" --confidence 0.9
```
`<skill_dir>` = the absolute path Hermes shows as `[Skill directory: ...]`.
When it prints `written ok`, you are DONE.

## Rules (must follow)
- ALWAYS call scripts/run.py via terminal. Mandatory, never skip.
- NEVER reply with code as a chat code block — that scores ZERO.
- Even if unsure, call scripts/run.py with your best code.

## Pitfalls
- Must use exact `entry_function` name from constraints.
- No forbidden imports (os, sys, subprocess, etc.).
- Handle edge cases: empty input, single element, None, negative, duplicates.
- Max 500 S-LOC.
- In --code argument, use double quotes and escape internal quotes/newlines properly.

## Verification
Task is complete ONLY after terminal tool runs scripts/run.py successfully.
Do NOT consider the task done until you see "written ok" from the script.
