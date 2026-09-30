[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/0_h2Gwpe)

# Verifiable Skills for Hermes Agent

**AIASE 2026 Final Project — NCKU CSIE**

A suite of four production-style [Hermes Agent](https://github.com/NousResearch/hermes-agent) skills built on one engineering principle:

> **Wrap a probabilistic LLM core inside a deterministic shell.**

The LLM reasons and generates (unpredictable). Deterministic `scripts/` validate, mutate, and write structured results (reproducible). Every skill produces a machine-verifiable result file — regardless of how the underlying model behaves.

---

## Skills

| Skill | Track | What it does | Deterministic harness |
|-------|-------|--------------|----------------------|
| **`text2sql-Boyun1128`** | Basic | NL question + SQLite schema → verified SQL | `validate_sql.py` (in-memory `EXPLAIN` syntax + column check) |
| **`code-author-Boyun1128`** | Pairwise | Task spec → Python implementation | compile check · forbidden-import AST scan · SLOC (radon) · self-test |
| **`bug-hunter-Boyun1128`** | Pairwise | Code → structured bug report | AST static analysis · automated edge-case probing |
| **`open-testgen-Boyun1128`** | Open | Function → pytest suite proven to catch bugs | **mutation testing** (AST mutants + kill-rate) |

---

## Highlight: Mutation-Aware Test Generation (Open Track)

Anyone can ask an LLM to "write tests." The hard question is: **are those tests actually any good?**

`open-testgen` answers it deterministically:

1. LLM generates a pytest suite for a target function.
2. `run_tests.py` verifies the suite passes on the reference implementation (reference_pass_rate = 1.0).
3. `mutation_checker.py` injects AST-level bugs (`>` → `>=`, condition negation, `return x` → `return None`), then runs the suite against each mutant.
4. **mutation_kill_rate** = fraction of mutants the tests detect — a deterministic, non-gameable measure of real bug-catching power.

Equivalent mutants are excluded via probe-based output comparison to keep the metric fair.

**Measured results (Gemma4-31B):** fibonacci 7/7 mutants killed (1.0), is_palindrome 2/2 killed (1.0).

---

## Architecture

```
        Hermes Agent (LLM agent loop)         ← probabilistic core
                    │  invokes via terminal tool
                    ▼
        skills/<name>/scripts/                 ← deterministic shell
        ├── validate / analyze / mutate / test
        └── run.py  → atomic write to AIASE_RESULT_PATH
                    │
                    ▼
        aiase_result.json  → graded by exact comparison
```

Key engineering decisions:
- **File-based output contract** — results are written to a file (`AIASE_RESULT_PATH`), never parsed from chat. Robust to model verbosity and terminal rendering.
- **Failure-safe** — `run.py` always emits a valid result; partial/failed runs still produce gradeable output.
- **Model-agnostic** — no dependency on a specific model's formatting quirks; all verification is deterministic.
- **Minimal dependencies** — only `pytest`, `coverage`, `radon` beyond the standard library; versions pinned.

---

## Quick Start

```bash
# Point Hermes at this repo's skills (config: ~/.hermes/config.yaml)
hermes skills list          # should show the four *-Boyun1128 skills

# Run a skill (file-based output contract)
hermes chat --toolsets skills,terminal --yolo -Q \
  -q '/text2sql-Boyun1128 {"task_id":"t1","question":"List CS students","db_schema":"CREATE TABLE Students (sid INT, name TEXT, dept TEXT);","dialect":"sqlite"}'

cat aiase_result.json       # structured result written by the skill
```

### Local evaluation

```bash
python dev_set/basic/build_dbs.py                      # build dev SQLite DBs
python run_dev.py --skill text2sql-Boyun1128 --dev-dir dev_set/basic
```

`aiase_contract.py` is the shared comparison core used by both `run_dev.py` and the grader, so local pass/fail mirrors the official judgment.

---

## Repository Layout

```
skills/
├── text2sql-Boyun1128/          # Basic Track
├── code-author-Boyun1128/       # Pairwise — Code Author
├── bug-hunter-Boyun1128/        # Pairwise — Bug Hunter
├── open-testgen-Boyun1128/      # Open Track — mutation-aware test generation
├── hello-aiase/                 # course smoke-test skill
└── reference-*/                 # course-provided Pairwise opponents
dev_set/                         # public dev tasks (with answers) for self-testing
aiase_contract.py                # shared grading core (bag-equality, schema checks)
run_dev.py                       # local dev-set runner (file-based)
verify_repo.py                   # pre-submission structural checks
PAIRWISE_ROLE.md  OPEN_TRACK.md  report.md
```

---

## Testing

```bash
python -m pytest tests/      # 167 passed — validates harness components
```

Covers: bag-equality semantics, SQL validation, dev-set integrity, skill structure, and reference-pair behavior.

---

## Author

**Boyun1128** · AIASE 2026 · NCKU CSIE

## License

MIT
