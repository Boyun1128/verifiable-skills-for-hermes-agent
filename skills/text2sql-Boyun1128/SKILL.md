---
name: text2sql-Boyun1128
description: Convert a natural-language question + SQLite schema into verified SQL, then write the result via scripts/run.py (file-based output contract).
version: 2.0.0
metadata:
  hermes:
    tags: [sql, text2sql, data, aiase]
    category: data
    requires_toolsets: [terminal]
---

# text2sql-Boyun1128 (file-based output contract)

## When to Use
When the user sends `/text2sql-Boyun1128 {json}` with `task_id`, `question`, `db_schema`, `dialect`.

## Procedure
This task has exactly ONE required action: run `scripts/run.py` via the `terminal` tool.
The result is graded ONLY from the file that script writes. Your chat text is ignored.

Step 1. Read `question` and `db_schema`. Compose one correct SQLite SELECT query.
Step 2. Use the `terminal` tool to run scripts/run.py with your SQL. This is the ONLY way to finish.

### Worked Example
Input: `{"task_id":"ex1","question":"List CS student names","db_schema":"CREATE TABLE Students (sid INTEGER, name TEXT, dept TEXT);","dialect":"sqlite"}`

Your terminal command (this is the ENTIRE response — no chat text, just the tool call):
```
python3 <skill_dir>/scripts/run.py --task_id "ex1" --sql "SELECT name FROM Students WHERE dept = 'CS'" --rationale "Filter Students by dept=CS, select name" --confidence 0.9
```
`<skill_dir>` = the absolute path Hermes shows as `[Skill directory: ...]`.
When it prints `written ok`, you are DONE.

## Rules (must follow)
- ALWAYS call scripts/run.py via terminal. This is mandatory, never skip it.
- NEVER reply with SQL as a chat code block — that scores ZERO.
- Even if unsure, call scripts/run.py with your best SQL.

## Pitfalls
- SQL: single statement, read-only SQLite. No CTE, no window functions.
- All columns/tables must exist in schema.
- Use DISTINCT for unique results.
- Wrap the --sql value in double quotes; SQL string literals use single quotes.
- **"every / all X satisfy Y" (universal quantification)**: express as double-negation
  `NOT EXISTS (... WHERE NOT Y)` — i.e. "there is no X that fails Y". Do NOT use a simple WHERE.
- **"at least one / any X satisfies Y" (existential)**: use `EXISTS (...)` or `IN (...)`.
- For multi-part conditions ("(a) ... and (b) ..."), translate each clause separately then AND them.

## Verification
Task complete ONLY after terminal runs scripts/run.py and prints "written ok".
