---
name: bug-hunter-Boyun1128
description: Analyze Python code for bugs, then write result via scripts/run.py (file-based output contract).
version: 2.0.0
metadata:
  hermes:
    tags: [code-review, bug-detection, python, analysis, aiase]
    category: code
    requires_toolsets: [terminal]
---

# bug-hunter-Boyun1128 (file-based output contract)

## When to Use
When the user sends `/bug-hunter-Boyun1128 {json}` with `task_id`, `code`, `task_description`.

## Procedure
This task has exactly ONE required action: run `scripts/run.py` via the `terminal` tool.
The result is graded ONLY from the file that script writes. Your chat text is ignored.

Step 1. Read the code and task description. Decide: is it buggy or clean? If buggy, identify each bug's line_start, line_end, severity, type, description, suggested_fix.
   Bug types: off_by_one, null_deref, type_error, logic_error, edge_case, api_misuse, inefficient, unhandled_input.
   Severities: critical, high, medium, low.
Step 2. Use the `terminal` tool to run scripts/run.py. This is the ONLY way to finish.

### Worked Example (clean code)
```
python3 <skill_dir>/scripts/run.py --task_id "ex1" --verdict "clean" --bugs "[]" --confidence 0.9
```

### Worked Example (buggy code — empty input crash at line 2)
```
python3 <skill_dir>/scripts/run.py --task_id "ex1" --verdict "buggy" --bugs '[{"line_start":2,"line_end":2,"severity":"high","type":"edge_case","description":"IndexError on empty input","suggested_fix":"if not x: return []"}]' --confidence 0.85
```
`<skill_dir>` = the absolute path Hermes shows as `[Skill directory: ...]`.
When it prints `written ok`, you are DONE.

## Rules (must follow)
- ALWAYS call scripts/run.py via terminal. Mandatory, never skip.
- NEVER reply with your analysis as chat text only — that scores ZERO.
- Even if uncertain, call scripts/run.py with your best judgment.

## Pitfalls
- Do NOT report false positives on clean code (heavily penalized).
- severity must match actual impact.
- bug.type must be from the allowed enum.
- Line numbers are 1-indexed based on the code string.
- Do NOT mark style issues as critical.

## Verification
Task is complete ONLY after terminal tool runs scripts/run.py successfully.
Do NOT consider the task done until you see "written ok" from the script.
