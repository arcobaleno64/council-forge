# 開始使用

## 前置需求

- **Python 3.11** — 執行驗證腳本所需
- **Git** — 版本控制
- **Claude Code** — CLI-first 協調者 agent（僅在 VS Code / Copilot 情境才使用 VS Code 擴充功能）
- **Gemini CLI** — 研究 agent（選配，完整工作流所需）
- **Codex CLI** — 實作 agent（選配，完整工作流所需）
- **PyYAML** — `pip install -r requirements.txt`

## 快速上手 — 新專案

```bash
# 1. 在本機複製 source template repo（以 .council-forge-source-repo 標記）
git clone https://github.com/arcobaleno64/council-forge.git council-forge
cd council-forge

# 1.5. 初始化 external/ 下的必要整合（submodule）
git submodule update --init --recursive

# 2. 建立你的下游專案，把 template/* 內容複製到「該專案的根目錄」
#    （下游屬 downstream terminal repo，不可再保留 nested template/）
# cp -r template/* <your-project-root>/
# cd <your-project-root>

# 3. 替換 CLAUDE.md 中的 placeholder（無 fork 則移除 fork 區段）
#    {{PROJECT_NAME}}, {{REPO_NAME}}, {{UPSTREAM_ORG}}

# 4. 啟動驗證
python artifacts/scripts/guard_status_validator.py --task-id TASK-900 --auto-classify
python artifacts/scripts/update_repository_profile.py
python artifacts/scripts/guard_contract_validator.py --check-readme
python artifacts/scripts/guard_contract_validator.py
python artifacts/scripts/prompt_regression_validator.py --root .

# 5. （選配）執行紅隊演練
python artifacts/scripts/run_red_team_suite.py --phase all
```

完整啟動指引請參閱 [BOOTSTRAP_PROMPT.md](https://github.com/arcobaleno64/council-forge/blob/master/BOOTSTRAP_PROMPT.md)。

## 快速上手 — 既有專案

1. 將 `template/` 目錄內容複製到你的專案根目錄
2. 替換 CLAUDE.md 中的 placeholder
3. 執行上述相同的驗證指令

## 兩種初始化模式

| 模式 | 說明 |
|---|---|
| 完整版 | 含 fork 整合與 Gemini CLI 研究功能 |
| 最小版 | 無 fork、無 Gemini，適合輕量使用 |

詳見 `BOOTSTRAP_PROMPT.md`。
