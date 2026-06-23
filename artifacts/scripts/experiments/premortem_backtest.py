#!/usr/bin/env python3
"""Premortem Calibration Backtest — 回測 premortem 預測 vs verify 實際結果。

實驗 ②：拿既有 plan artifacts 的 `## Risks`（R1..Rn，含 Severity）當「事前預測」，
對照同一 task 的 verify artifact 實際結果（verified / FAIL / escalation / blocked），
產生一份校準資料集與彙總統計。屬純離線分析，零外部依賴、零風險，適合無人值守。

誠實邊界：plan 與 verify 不是嚴格 1:1 因果，所以本工具不宣稱「精確命中率」，
而是提供可供人工判讀的 calibration dataset：
  - 每個 task 的風險數、severity 分布、verify 結果摘要。
  - 「事前標 blocking 風險」與「事後 verify 出現負面結果」的交叉統計。

用法：
    python3 premortem_backtest.py
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent
PLANS_DIR = REPO_ROOT / "artifacts" / "plans"
VERIFY_DIR = REPO_ROOT / "artifacts" / "verify"

TAIPEI = dt.timezone(dt.timedelta(hours=8))
TASK_ID_RE = re.compile(r"(TASK-\d+)")
# 風險識別碼可能出現在多種格式：`- R1:`、`### R1`、`R1`(裸行)、`- **R1**`。
# 限定在行首（容許 bullet/header/emphasis 前綴）以避免誤抓內文中的 R\d+。
RISK_RE = re.compile(r"^[-*#>\s]*\**(R\d+)\b", re.MULTILINE)
SEVERITY_RE = re.compile(r"Severity:\s*([^\n（(]+)", re.IGNORECASE)


def now_iso() -> str:
    return dt.datetime.now(TAIPEI).isoformat(timespec="seconds")


def extract_section(text: str, header: str) -> str:
    """抓取 `## header` 到下一個 `## ` 之間的內容。"""
    lines = text.splitlines()
    out: List[str] = []
    capturing = False
    for line in lines:
        if line.strip().startswith("## "):
            if capturing:
                break
            capturing = line.strip().lower() == f"## {header}".lower()
            continue
        if capturing:
            out.append(line)
    return "\n".join(out)


def parse_plan_risks(plan_text: str) -> Dict:
    risks_block = extract_section(plan_text, "Risks")
    # 去重並保留出現順序（同一 R\d+ 在 header + 子項可能重複出現）。
    risk_ids = list(dict.fromkeys(RISK_RE.findall(risks_block)))
    # severity 出現在每個風險的子行；取第一個詞作分類（blocking / non-blocking）。
    severities = [s.strip().lower().split()[0] for s in SEVERITY_RE.findall(risks_block) if s.strip()]
    sev_dist: Dict[str, int] = {}
    for s in severities:
        sev_dist[s] = sev_dist.get(s, 0) + 1
    return {
        "risk_count": len(risk_ids),
        "risk_ids": risk_ids,
        "severity_distribution": sev_dist,
        "blocking_count": sev_dist.get("blocking", 0),
        "has_premortem": len(risk_ids) > 0,
    }


def parse_verify_outcome(verify_text: str) -> Dict:
    verified = len(re.findall(r"Result:\s*verified", verify_text, re.IGNORECASE))
    results_total = len(re.findall(r"^- Result:", verify_text, re.MULTILINE))
    # red-team summary 表格內的 FAIL 計數，例如 `| FAIL (gap findings) | 2 |`
    fail_rows = re.findall(r"\|\s*FAIL[^|]*\|\s*(\d+)", verify_text)
    redteam_fail = sum(int(n) for n in fail_rows)
    escalated = len(re.findall(r"ESCALATED", verify_text))
    blocked = bool(re.search(r"\bblocked\b", verify_text, re.IGNORECASE))
    has_build_guarantee = "Build Guarantee" in verify_text
    # 負面結果信號採「強訊號」：red-team FAIL，或有未通過(verified<total)的 result。
    # blocked / escalated 文字常為引述他 task 或 by-design 結果，雜訊高，僅作資訊欄不計入。
    negative_signal = redteam_fail > 0 or (results_total > 0 and verified < results_total)
    return {
        "results_total": results_total,
        "verified": verified,
        "redteam_fail": redteam_fail,
        "escalated": escalated,
        "blocked": blocked,
        "has_build_guarantee": has_build_guarantee,
        "negative_signal": negative_signal,
    }


def collect() -> List[Dict]:
    records: List[Dict] = []
    for plan_path in sorted(PLANS_DIR.glob("*.plan.md")):
        m = TASK_ID_RE.search(plan_path.name)
        if not m:
            continue
        task_id = m.group(1)
        plan_text = plan_path.read_text(encoding="utf-8", errors="replace")
        rec: Dict = {"task_id": task_id, "plan": parse_plan_risks(plan_text)}
        verify_path = VERIFY_DIR / f"{task_id}.verify.md"
        if verify_path.exists():
            verify_text = verify_path.read_text(encoding="utf-8", errors="replace")
            rec["verify"] = parse_verify_outcome(verify_text)
        else:
            rec["verify"] = None
        records.append(rec)
    return records


def aggregate(records: List[Dict]) -> Dict:
    with_both = [r for r in records if r["verify"] is not None]
    with_premortem = [r for r in records if r["plan"]["has_premortem"]]
    risk_counts = [r["plan"]["risk_count"] for r in with_premortem]
    # 2x2 校準交叉表：事前是否標 blocking 風險 × 事後是否出現負面信號
    cells = {"pred_neg_act_neg": 0, "pred_neg_act_pos": 0, "pred_pos_act_neg": 0, "pred_pos_act_pos": 0}
    for r in with_both:
        predicted = r["plan"]["blocking_count"] > 0  # 事前預測有 blocking 風險
        actual = r["verify"]["negative_signal"]      # 事後實際出現負面結果
        key = f"pred_{'pos' if predicted else 'neg'}_act_{'pos' if actual else 'neg'}"
        cells[key] += 1
    return {
        "plans_total": len(records),
        "plans_with_premortem": len(with_premortem),
        "plans_with_verify": len(with_both),
        "avg_risks_per_premortem": round(sum(risk_counts) / len(risk_counts), 2) if risk_counts else 0,
        "max_risks": max(risk_counts) if risk_counts else 0,
        "min_risks": min(risk_counts) if risk_counts else 0,
        "tasks_with_negative_verify": sum(1 for r in with_both if r["verify"]["negative_signal"]),
        "calibration_2x2": cells,
    }


def render_markdown(agg: Dict, records: List[Dict]) -> str:
    c = agg["calibration_2x2"]
    flagged = [
        r for r in records
        if r["verify"] and r["verify"]["negative_signal"]
    ]
    lines = [
        "# Premortem Calibration Backtest — 校準報告",
        "",
        "## Metadata",
        f"- Generated At: {now_iso()}",
        "- Timezone: Asia/Taipei (+08:00)",
        f"- Corpus: `artifacts/plans/*.plan.md` × `artifacts/verify/*.verify.md`",
        "",
        "## Corpus Summary",
        "",
        f"- Plans total: {agg['plans_total']}",
        f"- Plans with premortem (R1..Rn): {agg['plans_with_premortem']}",
        f"- Plans with matching verify: {agg['plans_with_verify']}",
        f"- Avg risks per premortem: {agg['avg_risks_per_premortem']} (min={agg['min_risks']}, max={agg['max_risks']})",
        f"- Tasks with negative verify signal: {agg['tasks_with_negative_verify']}",
        "",
        "## Calibration 2×2 (預測 blocking 風險 × verify 負面信號)",
        "",
        "| | Actual: 負面信號 | Actual: 乾淨 |",
        "|---|---:|---:|",
        f"| **Pred: 有 blocking 風險** | {c['pred_pos_act_pos']} (TP) | {c['pred_pos_act_neg']} (FP) |",
        f"| **Pred: 無 blocking 風險** | {c['pred_neg_act_pos']} (FN) | {c['pred_neg_act_neg']} (TN) |",
        "",
        "> 說明：plan 與 verify 非嚴格 1:1 因果，本表為可判讀的校準資料集，非精確命中率。",
        "> FN（事前沒標 blocking、事後卻出現負面信號）最值得回來人工檢視。",
        "",
        "## Tasks with negative verify signal (建議回來檢視)",
        "",
        "| Task | Premortem risks | Blocking | RedTeam FAIL | Escalated | Blocked |",
        "|---|---:|---:|---:|---:|:--:|",
    ]
    for r in sorted(flagged, key=lambda x: x["task_id"]):
        v = r["verify"]
        p = r["plan"]
        lines.append(
            f"| `{r['task_id']}` | {p['risk_count']} | {p['blocking_count']} | "
            f"{v['redteam_fail']} | {v['escalated']} | {'yes' if v['blocked'] else 'no'} |"
        )
    if not flagged:
        lines.append("| (none) | | | | | |")
    lines.append("")
    return "\n".join(lines) + "\n"


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Premortem calibration backtest over plan/verify corpus.")
    p.add_argument("--output-dir",
                   default=str(REPO_ROOT / "artifacts" / "experiments" / "premortem_backtest"),
                   help="輸出目錄")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    records = collect()
    agg = aggregate(records)
    payload = {"generated_at": now_iso(), "aggregate": agg, "records": records}
    (out_dir / "backtest_results.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "backtest_report.md").write_text(
        render_markdown(agg, records), encoding="utf-8")

    print(f"[backtest] plans={agg['plans_total']} with_premortem={agg['plans_with_premortem']} "
          f"with_verify={agg['plans_with_verify']}")
    print(f"[backtest] negative-verify tasks={agg['tasks_with_negative_verify']}")
    print(f"[backtest] outputs: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
