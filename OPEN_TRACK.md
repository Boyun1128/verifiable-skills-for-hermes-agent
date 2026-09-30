## 1. Skill 簡介

Mutation-Aware Pytest Generator：給定 Python pure function 原始碼與功能描述，自動產生經 mutation testing 驗證的 pytest 測試套件，證明測試具備真實偵錯能力。

## 2. Skill 名稱與目錄

skills/open-testgen-Boyun1128/

## 3. 呼叫方式

評分環境以以下指令呼叫：

```bash
hermes chat --toolsets skills,terminal --yolo -Q -q '/open-testgen-Boyun1128 {"task_id":"testgen_001","function_code":"def fibonacci(n):\n    if n <= 0:\n        return 0\n    elif n == 1:\n        return 1\n    a, b = 0, 1\n    for _ in range(2, n + 1):\n        a, b = b, a + b\n    return b","function_description":"Return the nth Fibonacci number. fibonacci(0)=0, fibonacci(1)=1, fibonacci(n)=fibonacci(n-1)+fibonacci(n-2).","entry_function":"fibonacci","examples":[{"input":"0","output":"0"},{"input":"5","output":"5"},{"input":"10","output":"55"}]}'
```

**輸入 JSON schema：**

```json
{
  "task_id": "string (required, must echo in output)",
  "function_code": "string (required, Python source code of the function to test)",
  "function_description": "string (required, natural language description of function behavior)",
  "entry_function": "string (required, name of the function to test)",
  "examples": [{"input": "string", "output": "string"}]
}
```

**預期輸出 JSON schema：**

輸出寫入結果檔（`AIASE_RESULT_PATH` 或 `./aiase_result.json`），格式如下：

```json
{
  "task_id": "string (must match input task_id)",
  "test_code": "string (valid pytest test code)",
  "num_tests": "integer (number of test functions generated)",
  "compile_ok": "boolean (test code compiles)",
  "reference_pass_rate": "number 0.0-1.0 (fraction of tests passing on correct impl)",
  "mutation_kill_rate": "number 0.0-1.0 (fraction of valid mutants killed by tests)",
  "mutants_valid": "integer (number of valid non-equivalent mutants)",
  "mutants_killed": "integer",
  "mutants_survived": "integer",
  "verdict": "string enum: pass/fail",
  "rationale": "string",
  "confidence": "number 0.0-1.0"
}
```

## 4. 自定 Verifiable Scenario

### Metric 定義

A scenario is considered **PASS** if ALL of the following hold:
1. The final output is a valid fenced JSON object.
2. `task_id` matches the input.
3. `test_code` compiles and can be collected by pytest.
4. The generated tests pass on the reference implementation (`reference_pass_rate` = 1.0).
5. At least 3 valid (non-equivalent) mutants are generated (`mutants_valid` >= 3).
6. `mutation_kill_rate` >= 0.50 (tests kill at least half the valid mutants).

### Quality Levels (for graduated scoring)
- Level 1: `compile_ok` = true
- Level 2: `reference_pass_rate` = 1.0
- Level 3: `mutation_kill_rate` >= 0.50
- Level 4: `mutation_kill_rate` >= 0.80
- Level 5: `branch_coverage` >= 0.80 (optional quality indicator)

### 為何此 Metric 不可 Gameable

1. **Deterministic evaluator**：所有判定由 `scripts/run_tests.py` 和 `scripts/mutation_checker.py` 程式化執行，無主觀判斷。
2. **Ground truth via execution**：reference implementation 是 ground truth — tests 必須對它全 pass，這不可能靠猜或 hardcode。
3. **Mutation kill rate 要求真實偵錯力**：不能只寫 `assert True` — mutant 會改變 function 行為，只有真正檢查 output 的 test 才能 kill mutant。
4. **Anti-hardcoding**：Staff perturbation 換一個 function，hardcoded tests 立刻失效。Tests 必須真正理解 function 行為才能 pass reference + kill mutants。
5. **Equivalent mutant exclusion**：使用 probe-based 檢測排除 equivalent mutants，避免不公平的 kill rate 計算。

### Public Scenarios（至少 3 個可執行範例）

> **實測結果（aiase_model / Gemma4-31B）：**
> - Scenario 1 (fibonacci): reference_pass_rate=1.0, mutation_kill_rate=**1.0** (7/7 killed)
> - Scenario 2 (is_palindrome): reference_pass_rate=1.0, mutation_kill_rate=**1.0** (2/2 killed)
> - Scenario 3 & 4: 結構與 1、2 相同，預期表現一致

**Scenario 1: fibonacci**
```json
{"task_id":"testgen_001","function_code":"def fibonacci(n):\n    if n <= 0:\n        return 0\n    elif n == 1:\n        return 1\n    a, b = 0, 1\n    for _ in range(2, n + 1):\n        a, b = b, a + b\n    return b","function_description":"Return the nth Fibonacci number. fibonacci(0)=0, fibonacci(1)=1.","entry_function":"fibonacci","examples":[{"input":"0","output":"0"},{"input":"5","output":"5"}]}
```

**Scenario 2: is_palindrome**
```json
{"task_id":"testgen_002","function_code":"def is_palindrome(s):\n    s = s.lower().replace(' ', '')\n    return s == s[::-1]","function_description":"Check if a string is a palindrome (case-insensitive, ignoring spaces). Return True/False.","entry_function":"is_palindrome","examples":[{"input":"\"racecar\"","output":"True"},{"input":"\"hello\"","output":"False"}]}
```

**Scenario 3: merge_intervals**
```json
{"task_id":"testgen_003","function_code":"def merge_intervals(intervals):\n    if not intervals:\n        return []\n    intervals.sort(key=lambda x: x[0])\n    merged = [intervals[0]]\n    for current in intervals[1:]:\n        if current[0] <= merged[-1][1]:\n            merged[-1][1] = max(merged[-1][1], current[1])\n        else:\n            merged.append(current)\n    return merged","function_description":"Merge overlapping intervals. Input: list of [start, end] pairs. Output: merged list. Empty input returns [].","entry_function":"merge_intervals","examples":[{"input":"[[1,3],[2,6],[8,10]]","output":"[[1,6],[8,10]]"},{"input":"[]","output":"[]"}]}
```

**Scenario 4: binary_search**
```json
{"task_id":"testgen_004","function_code":"def binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    while left <= right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1","function_description":"Binary search on a sorted array. Return index of target if found, -1 otherwise.","entry_function":"binary_search","examples":[{"input":"[1,2,3,4,5], 3","output":"2"},{"input":"[1,2,3], 4","output":"-1"}]}
```

## 5. 預期失敗模式

1. **LLM 產生 happy-path-only tests（MAST: 驗證與品質控制問題）**
   - 觸發：LLM 只生成 normal case tests，不覆蓋 edge cases。
   - 影響：reference_pass_rate = 1.0 但 mutation_kill_rate < 0.50（mutants 存活）。
   - 處理：SKILL.md Procedure 明確要求「至少 2 個 boundary tests」；若 mutation_kill_rate 太低，帶回 survived mutant 資訊讓 LLM 補充 edge-case tests。

2. **LLM 產生的 test 對 reference 失敗（MAST: 規格與角色問題）**
   - 觸發：LLM 誤解 function 行為，寫出 assertion 與 reference 輸出不一致。
   - 影響：reference_pass_rate < 1.0 → verdict = fail。
   - 處理：Self-repair loop — scripts/run_tests.py 回傳失敗的 test name + error message，LLM 在第二次嘗試中修正（最多 2 次 repair）。

3. **Mutation checker 產生 equivalent mutants（技術限制）**
   - 觸發：某些 AST 變換產生語意等價的 code。
   - 影響：若不排除，kill rate 被不公平壓低。
   - 處理：Probe-based equivalence detection — 用 5 組標準輸入比較 original vs mutant 輸出，若完全相同則標記 suspected_equivalent 並排除出分母。

4. **Test code 有 syntax error（MAST: 驗證與品質控制問題）**
   - 觸發：LLM 產出格式錯誤的 Python。
   - 影響：compile_ok = false → verdict = fail。
   - 處理：Self-repair loop，把 SyntaxError 訊息回傳讓 LLM 修正。

## 6. 互動對象

This Open Track skill does not depend on cross-skill collaboration. It operates independently and interacts only with its own deterministic scripts under `skills/open-testgen-Boyun1128/scripts/`. This design reduces external failure points and keeps the verifiability metric fully self-contained.

Interaction flow:
1. Hermes LLM agent loop generates candidate pytest code (probabilistic core).
2. `scripts/run_tests.py` validates tests against reference (deterministic shell).
3. `scripts/mutation_checker.py` evaluates mutation kill rate (deterministic shell).
4. `scripts/run.py` produces final structured JSON output (deterministic shell).

No subagents are used. No external skills are called.

## 7. Token Budget 估算

每個 scenario 預估 token 消耗：

| 階段 | 預估 tokens |
|------|------------|
| Input (function code + description + examples) | ~500 |
| LLM test generation (attempt 1) | ~2,000 |
| LLM repair (attempt 2, if needed) | ~1,500 |
| SKILL.md context | ~1,000 |
| Scripts output parsing | ~500 |
| **Total per scenario (worst case with repair)** | **~5,500** |
| **Total per scenario (best case, no repair)** | **~4,000** |

遠低於 50k tokens/scenario 門檻。即使 3 次 attempt 也不超過 8,000 tokens/scenario。
