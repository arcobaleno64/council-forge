# 架構流程圖 Architecture Diagram

完整架構與流程一覽：**三代理**（Claude · Gemini · Codex）、**六階五關**、**九型工件**、**驗證關卡組（Guard Battery）**、**下游散布**，以及 **PDCA × TAO 治理雙環**。

Gate 對應以 [`docs/orchestration.md`](https://github.com/arcobaleno64/council-forge/blob/master/docs/orchestration.md) 為準：**Gate A = Research · B = Planning · C = Code · D = Verification · E = Closure（blocked resume）**。

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontSize":"15px","fontFamily":"Segoe UI, Microsoft JhengHei, sans-serif"}}}%%
flowchart TB
    %% ===== Council Forge — 完整架構流程圖 (Saturated) =====
    classDef agent fill:#4338CA,stroke:#1E1B4B,color:#ffffff,stroke-width:2px;
    classDef stage fill:#0D9488,stroke:#042F2E,color:#ffffff,stroke-width:2px;
    classDef gate fill:#F59E0B,stroke:#7C2D12,color:#1F2937,stroke-width:2px;
    classDef artifact fill:#2563EB,stroke:#1E3A8A,color:#ffffff;
    classDef guard fill:#DC2626,stroke:#7F1D1D,color:#ffffff;
    classDef ci fill:#475569,stroke:#0F172A,color:#ffffff;
    classDef down fill:#9333EA,stroke:#4C1D95,color:#ffffff;
    classDef gov fill:#CA8A04,stroke:#713F12,color:#ffffff,stroke-width:2px;

    GOV["治理雙環 Two-Layer Governance<br/>PDCA 跨任務宏觀環 × TAO/ReAct 單步微觀環<br/>P = task + research + plan（含 premortem） · D = code · C = verify（Build Guarantee） · A = improvement + decision → 回饋下一輪 Plan"]:::gov

    subgraph AG["三代理 · 職責分工 Role Split"]
        direction TB
        CLA["Claude Code<br/>Orchestrator<br/>決策 · 驗收 · 最後整合"]:::agent
        GEM["Gemini CLI<br/>Research + Memory Curator<br/>read-only · 每 claim 須引用"]:::agent
        COD["Codex CLI<br/>Implementation"]:::agent
        subgraph SUB["Codex 子代理 Subagents"]
            direction LR
            IMP["Implementer"]:::agent
            TST["Tester"]:::agent
            VER["Verifier"]:::agent
            REV["Reviewer"]:::agent
        end
        COD --> SUB
    end

    subgraph FLOW["核心流程 Pipeline · 不得跳步（stage 6 = Closure；done 為狀態）"]
        direction TB
        I["Intake<br/>建立 task"]:::stage
        GA{"Gate A<br/>research"}:::gate
        R["Research"]:::stage
        GB{"Gate B<br/>plan 核可"}:::gate
        P["Planning<br/>+ Premortem"]:::stage
        GC{"Gate C<br/>code"}:::gate
        C["Coding<br/>+ TAO/ReAct 微環"]:::stage
        T["testing"]:::stage
        GD{"Gate D<br/>verify"}:::gate
        V["Verification（verifying）<br/>+ Build Guarantee"]:::stage
        D(["done（狀態）"]):::stage
        CL["Closure / Act<br/>improvement + decision + ledger"]:::stage
        GE{"Gate E<br/>blocked resume"}:::gate
        BL["Blocked"]:::guard

        I --> GA --> R --> GB --> P --> GC --> C --> T --> GD --> V
        V -->|PASS| D --> CL
        CL -. 回饋下一輪 Plan .-> P
        V -->|FAIL 回退| C
        V -->|阻塞| BL
        BL --> GE
        GE -->|improvement applied| P
        I -. lightweight 可跳 .-> GB
    end

    %% routing
    CLA -->|orchestrate| I
    CLA -->|研究與策展| GEM
    CLA -->|已規劃實作| COD
    GEM --> R
    COD --> C

    subgraph ART["Artifact-First · 9 型工件 single source of truth"]
        direction LR
        A1["task"]:::artifact
        A2["research"]:::artifact
        A3["plan"]:::artifact
        A4["code"]:::artifact
        A5["test"]:::artifact
        A6["verify"]:::artifact
        A7["decision"]:::artifact
        A8["improvement<br/>draft→approved→applied"]:::artifact
        A9["status.json"]:::artifact
        REG["registry<br/>decision_registry.json"]:::artifact
        LED["PROCESS_LEDGER.md<br/>cold-start 入口"]:::artifact
    end
    I --> A1
    R --> A2
    P --> A3
    C --> A4
    T --> A5
    V --> A6
    BL --> A7
    CL --> A8
    A8 -->|applied| GE
    I --> A9
    A7 --> REG
    A8 --> LED

    subgraph GU["驗證關卡組 Guard Battery + CI"]
        direction TB
        G1["guard_status_validator.py<br/>schema · state machine · Gate A–E · scope-drift"]:::guard
        G2["guard_contract_validator.py<br/>root↔template↔Obsidian sync · prompt 對齊"]:::guard
        G3["run_quality_gates.py<br/>baseline QC + waiver"]:::guard
        G4["prompt_regression_validator.py"]:::guard
        G5["run_red_team_suite.py<br/>30 靜態案 + live drill"]:::guard
        G6["Security gates<br/>SAST · SBOM · SCA · security.txt · release"]:::guard
        CI["CI<br/>workflow-guards.yml<br/>security-scan.yml"]:::ci
        G1 --> CI
        G2 --> CI
        G3 --> CI
        G4 --> CI
        G5 --> CI
        G6 --> CI
    end
    GA -.-> G1
    GB -.-> G1
    GC -.-> G1
    GD -.-> G1
    GE -.-> G1

    subgraph DS["下游散布 Template → Downstream"]
        direction LR
        TMPL["template/<br/>EXACT_SYNC"]:::down
        SNAP["snapshot_manifest.py"]:::down
        MAN[".well-known/<br/>release-manifest.json"]:::down
        PROP["propagate_downstream.py"]:::down
        DOWN["Downstream terminal repos<br/>Sentinel · Verso · Vero · LINE-BOT"]:::down
        SNAPJ[".council-forge/<br/>release-snapshot.json"]:::down
        TMPL --> SNAP --> MAN --> PROP --> DOWN --> SNAPJ
    end
    G2 -.-> TMPL

    GOV -.治理.-> FLOW
```

> 來源：`README.md`、`CLAUDE.md`、`docs/orchestration.md`、`docs/workflow_state_machine.md`。
