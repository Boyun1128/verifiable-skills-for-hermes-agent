# 期末報告 — AIASE 2026 Final Project

**學生：** Boyun1128
**課程：** Generative AI Application Systems and Engineering (AIASE 2026)
**日期：** 2026/06/16

---

## 1. 設計決策

### 1.1 整體架構：Deterministic Shell Wrapping Probabilistic Core

本專案所有 skill 的設計遵循同一原則：LLM（Hermes Agent loop）負責推理與生成（probabilistic core），scripts/ 負責驗證、結果寫檔（deterministic shell）。最終輸出一律由 `scripts/run.py` 以原子寫入方式寫進結果檔（`AIASE_RESULT_PATH`），確保即使 LLM 推理不穩定，仍能產出可評分的結構化結果。

### 1.2 Basic Track: Text2SQL

**SKILL.md 設計理念：**
- Procedure 指導 Hermes 依序完成 schema 分析 → SQL 生成 → 語法驗證 → 寫入結果檔。
- Pitfalls 段落提示常見錯誤（多對多未去重、引用不存在的欄位、non-SQLite 語法）。

**Harness 策略（scripts/）：**
- `validate_sql.py`：使用 SQLite `:memory:` + `EXPLAIN` 驗證 SQL 語法正確性，支援多種呼叫方式（stdin JSON、CLI args、--sql/--schema flags），確保 Hermes 無論用什麼方式呼叫都能正確運作。
- `run.py`：file-based 輸出，原子寫入結果檔，接受 `--task_id --sql --rationale --confidence` 參數。

**設計取捨：**
- 選擇 EXPLAIN 而非 actual execution：因為手上沒有資料（schema 是空表），無法判斷結果對錯，但可確保語法正確。
- SQL 驗證設為「optional」而非強制：觀察到 Hermes 呼叫 validate_sql.py 時有時因 shell escape 問題（SQL 中的 single quotes）導致 JSON parse 失敗（exit 2），但 LLM 產出的 SQL 本身是正確的。讓 LLM 即使跳過驗證也能直接寫結果檔，避免因 harness 呼叫問題而遺失結果。

### 1.3 Pairwise Track

**Code Author：**
- `check_compile.py`：確保生成的 code 可編譯。
- `check_imports.py`：AST-based 分析，確認無禁用 import（包括動態 import __import__ 和 importlib）。
- `count_sloc.py`：使用 radon raw 計算 SLOC，確認不超過 500 行。
- `self_test.py`：生成邊界測試案例並執行，提前發現明顯 bug。
- `run.py`：file-based 輸出，含 task_id、code、loc、self_test_results、rationale、confidence。

**Bug Hunter：**
- `static_analysis.py`：AST-based pattern detection（未檢查空輸入、unguarded index access）。
- `edge_case_generator.py`：自動生成 10 種邊界輸入並在 subprocess 中執行，偵測 crash。
- `run.py`：file-based 輸出，接受 `--verdict`、`--bugs`（JSON array string）。
- 設計重點：避免 false positive（只在有強證據時才報 bug），severity 與影響相符。

### 1.4 Open Track: Mutation-Aware Pytest Generator

**設計理念：**
- 核心問題：「LLM 產出的測試真的能抓 bug 嗎？」
- 解法：用 mutation testing 作為 deterministic evaluator — 不是問 LLM 測試好不好，而是程式化地驗證「面對 AST-level 的 bug，測試能不能偵測到」。

**Verifiability Metric 設計：**
- reference_pass_rate = 1.0：tests 必須對正確實作全 pass（不是亂寫的）。
- mutation_kill_rate >= 0.50：tests 必須能殺掉至少一半的 mutants（有真實偵錯能力）。
- 兩者都是 deterministic binary 判定，完全程式化。

**Mutation types（3 種核心 mutation）：**
1. Boundary/Compare mutation (> ↔ >=, < ↔ <=, == ↔ !=)
2. Condition negation (if cond → if not cond)
3. Return mutation (return x → return None)

**Equivalent mutant 處理：**
- 使用 probe-based 檢測：以 16 組標準探測輸入（涵蓋 int、list、str、None）比較 original vs mutant 輸出。
- 若所有有效 probe 的輸出都相同 → 標記為 suspected_equivalent，排除出分母。
- 若沒有任何 probe 能正常執行 → 保守地不排除（視為 non-equivalent）。

---

## 2. 系統架構

```
┌─────────────────────────────────────────────────┐
│           Hermes Agent (Probabilistic Core)       │
│   LLM 推理：理解題目、產生 SQL/Code/Tests         │
└───────────────────────┬─────────────────────────┘
                        │ 用 terminal 工具呼叫 scripts/
                        ▼
┌─────────────────────────────────────────────────┐
│         scripts/ (Deterministic Shell)            │
│                                                   │
│  ┌──────────┐  ┌───────────┐  ┌──────────────┐  │
│  │validate  │  │mutation   │  │run.py        │  │
│  │_sql.py   │  │_checker.py│  │(寫結果檔)    │  │
│  └──────────┘  └───────────┘  └──────────────┘  │
│                                                   │
│  功能：語法驗證 · AST mutation · 測試執行          │
│       · SLOC 計算 · 原子寫檔 · Retry feedback     │
└─────────────────────────────────────────────────┘
                        │
                        ▼
         AIASE_RESULT_PATH (aiase_result.json)
                        │
                        ▼
              評分器讀檔 → bag_equal 比對
```

---

## 3. 失敗分析（附 log 證據）

### 遭遇的失敗與原因分析

| # | 失敗原因 | 觸發情境 | 解決辦法 | MAST 分類 |
|---|----------|----------|----------|-----------|
| 1 | validate_sql.py exit code 2 | SQL 含 single quotes 時 LLM 組裝的 echo 命令 JSON escape 不正確 | 讓 validate 為 optional，LLM 可直接寫結果 | (3) 驗證與品質控制 |
| 2 | Hermes 未使用 scripts/run.py 而自行輸出 JSON | 舊版未加 `-Q` flag，LLM 輸出被美化處理 | 更新到 file-based 輸出 + `-Q` flag | (1) 規格與角色 |
| 3 | 多個背景 job 同時寫同一檔案 | 開發時多次按下同一命令 | 確保只有一個 job 執行 | (2) 協調問題 |
| 4 | task_nl2sql_020 結果不一致（全稱量化 SQL 錯誤） | LLM 對「every patient older than 60」未用雙重否定 NOT EXISTS | SKILL.md Pitfalls 加入 universal quantification → 雙重否定的明確提示 | (3) 驗證與品質控制 |
| 5 | LLM 偶發不呼叫 scripts/run.py（no result file） | 複雜或問答式題目，LLM 在 chat 直接輸出 SQL 而跳過 tool call | 簡化 Procedure（6 步→2 步）+ worked example + 強制措辭 | (1) 規格與角色 |
| 6 | 誤把 gemini-2.5-flash 設為 default → 401 | team 權限只開 aiase_model，誤切模型導致全題 401 | 切回 aiase_model；理解 team-based model 權限 | (2) 協調問題 |

### 詳細失敗案例

#### 失敗案例 1: Shell Escape 導致 validate_sql.py 失敗 (exit code 2)

- **觸發條件：** SQL 中含有 single quote（如 `WHERE dept = 'CS'`），LLM 用 `echo '{"sql": "SELECT ... WHERE dept = \"CS\"", ...}'` 呼叫 validate_sql.py
- **Log 摘要：** `python3 scripts/validate_sql.py  0.1s [exit 2]` — JSON 裡的 `\"CS\"` 在 single-quoted echo 中不會被正確 escape
- **Root Cause：** Bash 的 single-quote 字串不解析 escape sequences。`\"` 在 `'...'` 裡是 literal 兩個字元 `\"` 不是 `"`，導致 JSON parse 失敗。
- **解決辦法：** 將 validate_sql.py 設為 optional 步驟（Procedure 中用 "Optionally validate"），讓 LLM 即使跳過驗證也能直接呼叫 run.py 寫結果。實測表明 LLM 的 SQL 正確率極高，驗證步驟主要防低級錯誤。

#### 失敗案例 2: 輸出格式被 Hermes 美化處理吃掉

- **觸發條件：** 未加 `-Q` flag 時，Hermes 的 rich terminal 渲染會把 ` ``` ` 標記吃掉
- **Log 摘要：** `grep -c '```json' /tmp/hermes_output.txt` → 結果為 0
- **Root Cause：** Hermes 的預設輸出模式會做 rich rendering，把 markdown code block 標記轉換成美化格式，stdout 中不再包含原始的 ` ``` ` 標記
- **解決辦法：** (1) 評分指令統一加 `-Q` flag；(2) 從「對話輸出 JSON」改為「file-based 寫結果檔」，完全不依賴 stdout 格式。

#### 失敗案例 3: LLM 偶發跳過 tool call（最關鍵的失敗模式）

- **觸發條件：** 某些題目（特別是「For each X, return...」這類直白問答式，或 depth-2 correlated subquery 等高推理量題目），LLM 把 SQL 直接印在對話而不呼叫 scripts/run.py。
- **Log 摘要（task_nl2sql_010）：**
  ```
  === RC: 0 ===
  === STDOUT ===
  ```sql
  SELECT T1.name, COUNT(T2.bid) FROM Authors AS T1 LEFT JOIN BookAuthors ...
  ```
  === RESULT ===
  NO FILE
  ```
  注意：SQL 本身完全正確，但結果檔沒被寫出 → 該題 0 分。
- **Root Cause：** Gemma4 的 tool-calling 是機率性的。當推理佔用較多 context 時，LLM 容易「以為任務完成」而省略最後的 tool call。這正是課程強調的 **probabilistic core 的不可靠性**。
- **解決辦法（harness engineering 迭代）：**
  1. 把 Procedure 從 6 步簡化到 2 步，降低 LLM 在中途「分心」的機率。
  2. 加入 worked example，讓 LLM 有可直接照抄的 tool call 範本。
  3. 用強制措辭（"MANDATORY"、"scores ZERO"）。
  - 效果：task_007（複雜 JOIN）從連續 3 次失敗 → 穩定通過；task_016（depth-2 correlated）連跑 3 次全 PASS。
- **殘留限制：** 仍無法在 Gemma4 上達到單次 100%（這是機率核心的本質）。助教公告正式評分用更強模型，tool-calling 穩定性更高。這也呼應課程主旨——**deterministic shell 能把格式、驗證、寫檔做到 100% 可靠，但「LLM 是否決定呼叫 shell」終究是機率性的**，這是 agentic 系統的根本張力。

#### 失敗案例 4: 全稱量化 SQL 邏輯錯誤（task_020）

- **觸發條件：** 問題要求「every patient ever seen ... is older than 60」（全稱量化）。LLM 初版用簡單 WHERE 過濾，邏輯錯誤，結果與 gold 不符（result differs from gold）。
- **Root Cause：** 全稱量化（∀）在 SQL 沒有直接語法，必須轉成雙重否定「不存在反例」(`NOT EXISTS (... WHERE NOT condition)`)。LLM 未自動套用此 pattern。
- **解決辦法：** 在 SKILL.md 的 Pitfalls 加入明確規則：「every/all X satisfy Y → `NOT EXISTS (... WHERE NOT Y)`」。加入後 task_020 即通過。這是典型的 **context engineering**——把領域知識編碼進 skill 的合約，補足機率核心的推理盲點。

### Mutation Testing 量化分析

| Scenario | reference_pass_rate | mutation_kill_rate | mutants_valid | mutants_killed | 分析 |
|----------|--------------------|--------------------|---------------|----------------|------|
| fibonacci | 1.0 | 1.0 | 7 | 7 | 所有 7 個 mutants 都被偵測到，包含 boundary (<=0 → <0)、condition negation、return mutation。LLM 產出的 tests 涵蓋了 n=0, n=1, n=5, n=10 等邊界。 |
| is_palindrome | 1.0 | 1.0 | 2 | 2 | function 較簡單（mutation 空間小），2 個 valid mutants 均被 case-insensitivity + boundary tests 殺掉。 |

**Dev set Basic Track 完整結果（aiase_model / Gemma4-31B）：**
- 整批跑 21 題（含 EXAMPLE）：18-19/21 PASS（86-90%）
- 所有產出結果的題目 SQL 邏輯正確（bag-equal 通過）
- 1-2 題偶發 "no result file"：LLM 隨機性未呼叫 tool（非 code 問題，重跑即通過）
- 助教公告正式評分使用更強模型，tool-calling 穩定性會更高

---

## 4. 若從頭來過，我會做什麼改變

1. **一開始就用 file-based 輸出**：我們最初的設計是讓 skill 在對話中輸出 fenced JSON block，後來發現 Hermes + `-Q` 的行為與預期不同。如果一開始就知道要用 file-based，可以省去中間的 debug 時間。

2. **validate_sql.py 改用 heredoc 或 tempfile 方式呼叫**：shell escape 問題浪費了不少 debug 時間。更好的做法是讓 SKILL.md 指導 LLM 先把 JSON 寫入 tempfile，再用 `python3 validate_sql.py < /tmp/input.json` 的方式呼叫，避免 echo 的 escape 問題。

3. **更早跑 verify_repo.py**：這個腳本能提前發現 naming、格式等問題，應該在第一個 commit 就跑。

---

## 5. 改進方向

1. **validate_sql.py 改用 tempfile 呼叫方式**：避免 shell escape 問題，提高驗證穩定性。
2. **Open Track 加入 self-repair loop**：當 mutation_kill_rate < 0.50 時，把 survived mutant 資訊回傳 LLM，讓它補充 edge-case tests。
3. **Bug Hunter 加入更多 edge-case 模式**：目前的 edge_case_generator.py 只有 10 種固定模式，可依 task_description 動態生成更有針對性的邊界輸入。
4. **跨模型驗證**：用 gemini-2.5-flash 跑一輪完整的 dev set，確保 model-agnostic 設計有效。

---

## 6. 引用說明

| 來源 | 用途 | 差異說明 |
|------|------|----------|
| [Hermes Agent GitHub](https://github.com/NousResearch/hermes-agent) | 平台理解、CLI 用法 | 依規格書使用，無改寫 |
| [agentskills.io](https://agentskills.io) | SKILL.md 格式規範 | 依標準撰寫 |
| Python `ast` module 文件 | mutation_checker.py 的 AST 操作 | 自行設計 mutation operators |
| pytest 官方文件 | 測試執行與收集方式 | 用於 run_tests.py 的 subprocess 呼叫 |
| 課程 starter repo 的 reference skills | 理解 file-based output pattern | 照範例改寫為自己的 run.py |

本專案所有 scripts/ 程式碼為個人原創，未直接複製任何第三方 skill 或 repo。AI coding assistant（Kiro）用於輔助理解 Hermes skill 機制、設計 scripts 架構、與除錯 shell escape 問題，最終設計決策與實作品質由學生負責。
