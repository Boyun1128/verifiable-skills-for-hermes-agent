#!/usr/bin/env python3
"""open-testgen / scripts/run.py — file-based 輸出契約入口（原子寫入結果檔）。

⚠️ 自帶 resolve_result_path，不 import aiase_contract（安裝後找不到 repo 根模組）。
"""
import os, sys, json, argparse


def resolve_result_path() -> str:
    return os.environ.get("AIASE_RESULT_PATH") or os.path.join(os.getcwd(), "aiase_result.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task_id", required=True)
    ap.add_argument("--test_code", required=True)
    ap.add_argument("--num_tests", type=int, default=0)
    ap.add_argument("--compile_ok", type=str, default="true")
    ap.add_argument("--reference_pass_rate", type=float, default=0.0)
    ap.add_argument("--mutation_kill_rate", type=float, default=0.0)
    ap.add_argument("--mutants_valid", type=int, default=0)
    ap.add_argument("--mutants_killed", type=int, default=0)
    ap.add_argument("--mutants_survived", type=int, default=0)
    ap.add_argument("--rationale", default="")
    ap.add_argument("--confidence", type=float, default=0.5)
    a = ap.parse_args()

    compile_ok = a.compile_ok.lower() in ("true", "1", "yes")

    # Determine verdict
    verdict = "pass"
    if not compile_ok:
        verdict = "fail"
    elif a.reference_pass_rate < 1.0:
        verdict = "fail"
    elif a.mutants_valid < 3:
        verdict = "fail"
    elif a.mutation_kill_rate < 0.50:
        verdict = "fail"

    result = {
        "task_id": a.task_id,
        "test_code": a.test_code,
        "num_tests": a.num_tests,
        "compile_ok": compile_ok,
        "reference_pass_rate": round(a.reference_pass_rate, 4),
        "mutation_kill_rate": round(a.mutation_kill_rate, 4),
        "mutants_valid": a.mutants_valid,
        "mutants_killed": a.mutants_killed,
        "mutants_survived": a.mutants_survived,
        "verdict": verdict,
        "rationale": a.rationale,
        "confidence": a.confidence,
    }

    path = resolve_result_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    os.replace(tmp, path)
    print(f"written ok -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
