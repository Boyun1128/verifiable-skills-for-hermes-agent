roles:
  - role: code-author
    skill_path: skills/code-author-Boyun1128/
  - role: bug-hunter
    skill_path: skills/bug-hunter-Boyun1128/

<!--
   Pairwise Track：兩個角色（Code Author + Bug Hunter）都要實作並提交。
   評分時，課程會隨機抽取其中一個角色，並與另一位同學隨機配對來評分。
   上方 roles list 同時宣告兩個 skill 的路徑。

   規則：
   1. roles 必須同時包含 code-author 與 bug-hunter 兩筆。
   2. 每筆的 role 只能是 code-author 或 bug-hunter，且不可重複。
   3. 每個 skill_path 必須指向實際存在、且能被 hermes skills list 看到的 skill 資料夾。
   4. 評分時課程會隨機抽取其中一個角色評分，並與另一位同學隨機配對。
   5. 若 PAIRWISE_ROLE.md 缺漏、格式錯誤、或任一 skill_path 不存在，Pairwise Track 0 分。

   配對對象由課程自動隨機指派，不得私下約定。
-->
