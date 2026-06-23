# Security Audit — 彙總報告

授權的自我安全評估(repo owner 要求)。由 5 個 read-only 審計 subagent 平行執行,
agent 僅讀碼、僅產出各自 findings 檔;改碼由協調者統一處理(single-writer)。

## Metadata
- Generated At: 2026-06-23 (Asia/Taipei, +08:00)
- Scope: `artifacts/scripts/**`、`.github/workflows/**`
- 方法:對抗性審計(B)+ CI/供應鏈審查(C)+ 業界 SAST 基線(A:Bandit/Semgrep)
- 詳細報告:見同目錄 `01`–`05`

## 攻擊面前提
本 repo 無部署中的網路服務(Python 腳本 + 治理文件型),故傳統 Web/網路滲透無標的。
真實攻擊面 = **會吃不可信輸入的工作流腳本**:artifact 內容、git diff replay、
GitHub PR 資料、archive 路徑、以及對這些輸入跑的 regex。下列發現皆環繞此面。

## 發現總表

| ID | 嚴重度 | 標題 | 位置 | 狀態 |
|---|---|---|---|---|
| REDOS-01 | **Critical** | `RESEARCH_SOURCES_ENTRY_PATTERN` 的 `.+\..+` 災難性回溯;~2KB 輸入 hang 15s | `guard_status_validator.py:174-176` | 實測確認 |
| REDOS-02 | **High** | `CITATION_PATTERN` 雙重無界填充;~40KB 輸入 hang 23.8s | `guard_helpers/markers.py:7-16`(+ `guard_status_validator.py:137-146` 重複) | 實測確認 |
| F-01 | **High** | SSRF + token 外洩:`urlopen` 跟隨 redirect 會把 `Authorization: Bearer` 轉送到 redirect 目標(可達內部主機);host 僅驗 base URL | `guard_status_validator.py:448-450` | 機制確認(bandit B310 佐證) |
| SEC-LEAK | Medium | 秘密掃描器把命中的整行 `excerpt` 印進 stdout/JSON/SARIF,等於把找到的 PAT/AWS key 複製進 CI log | `repo_security_scan.py:388-390,406,471-503` | 確認 |
| SEC-FN | Medium | 秘密規則漏抓:Slack `xox*`、Google `AIza*`、Stripe `sk_live_`(規則寫成 `sk-`)、AWS secret 後半、JWT、npm/SendGrid/PyPI | `repo_security_scan.py` STRUCTURED_SECRET_PATTERNS | 確認 |
| ARG-INJ | Medium | artifact 的 `Base Ref`/`Head Ref` 未驗證即進 `git rev-parse`,可注入 `--git-dir=` 類參數(影響有限:binding diff 用 SHA 驗證的 commit) | `guard_status_validator.py:595-604,699-700` | 確認 |
| CI-01 | Medium | `workflow_dispatch` inputs 經 `${{ }}` 直接拼進 `run:` shell(template-injection 類) | `large-scale-experiments.yml:50-51` | **已修(本次)** |
| CI-02 | Medium | 同 job 持 `contents: write` 且 checkout 保留 GITHUB_TOKEN → 被注入碼可 push 任意未保護分支 | `large-scale-experiments.yml:36-39` | 緩解(見下) |
| CI-03 | Low | weekly-council-audit 跑浮動 `@openai/codex@latest` 並同時持 write 權限 + secret | `weekly-council-audit.yml` | 待評估 |
| F-01b..F-07 | Low/Info | archive read 先讀後檢 size、Windows 路徑正規化、redirect-target 未逐次驗 allowlist、entropy 規則 gap 等 | 見 `01`/`05` | 記錄 |

完整 PoC 與修補建議見各分報。

## 已澄清(查核後無虞)
- **無** zip-slip(所謂 archive 是純文字路徑 manifest,非壓縮檔)、**無** 目錄穿越突破 `relative_to(resolved_root)` 容器檢查。
- **無** `shell=True` / `os.system` / `eval`/`exec` / `pickle` / `yaml.load`(全用 argv-form subprocess)。
- 內嵌 HTTP server 僅 `127.0.0.1` ephemeral port、daemon、context-managed 的測試 fixture,未對外暴露。
- host allowlist 對 userinfo@/大小寫/port/trailing-dot 繞過具抵抗力(用 `urlparse().hostname`)。
- 所有 workflow 的 `uses:` 皆 pin 40 字元 SHA;無 `pull_request_target` + 不可信 ref + secret 組合;`red_team/helpers.run_command` 是良好硬化範例。
- 自製 SAST 規則(STATIC_RULES/PYTHON_SAST_RULES/STRUCTURED_SECRET_PATTERNS)經查為線性,無 ReDoS。

## 建議優先序(remediation)
1. **REDOS-01(Critical)**:以欄位切割解析取代 `.+\..+`,或加每行長度上限 + wall-clock 預算。
2. **REDOS-02(High)**:收斂雙重填充(或加 `')' in item` precheck);**兩份**(root + template)同步修。
3. **F-01(High)**:自訂 redirect handler,跨 host 不轉送 `Authorization`;每次 redirect 重驗 allowlist。
4. **SEC-LEAK / SEC-FN(Medium)**:excerpt 改為遮罩;補秘密規則格式。

> ⚠️ 上述 1–4 多落在 `guard_*` 與秘密掃描器,屬 **security-critical 且 template-synced**(root + `template/` 兩份 + README 同步 + guard_contract_validator 驗證)。為避免無人值守期間改壞核心 guard / 破壞 sync 契約,**程式修補待指揮官核可後再執行**。本次先交付:評估報告 + 業界 SAST 工具(A)+ 低風險的 CI-01 修補。
