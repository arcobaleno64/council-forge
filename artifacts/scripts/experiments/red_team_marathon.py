#!/usr/bin/env python3
"""Red-Team Marathon — soak / stability experiment for the red-team suite.

實驗 ①：反覆執行 `run_red_team_suite.py`，觀察套件在多輪執行下是否「穩定」
（每一輪結果一致）、是否有 flaky case（結果在輪與輪之間翻轉）、執行時間是否漂移，
以及暫存 fixture 是否乾淨回收。屬離線、確定性、帶護欄的批次工作，適合無人值守。

設計重點：
- 護欄：--iterations 與 --max-minutes 任一達到即停止，避免失控。
- 確定性訊號：以每個 case 的 outcome(pass/fail) + exit code 作為比對基準，
  忽略 evidence 內含的隨機暫存路徑（uuid 後綴）。
- 產出：每輪一份 report + 一份彙總 JSON + 一份趨勢 markdown。

用法：
    python3 red_team_marathon.py --iterations 20 --max-minutes 60 --phase static
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPTS_ROOT = SCRIPT_DIR.parent  # artifacts/scripts
REPO_ROOT = SCRIPTS_ROOT.parent.parent
SUITE = SCRIPTS_ROOT / "run_red_team_suite.py"

# 重用既有 report 解析器，確保與 scorecard 工具同一套表格語意。
sys.path.insert(0, str(SCRIPTS_ROOT))
import aggregate_red_team_scorecard as agg  # noqa: E402

TAIPEI = dt.timezone(dt.timedelta(hours=8))


def now_iso() -> str:
    return dt.datetime.now(TAIPEI).isoformat(timespec="seconds")


def run_once(phase: str, report_path: Path) -> Dict:
    """跑一輪 suite，回傳該輪的結構化結果。"""
    start = time.monotonic()
    proc = subprocess.run(
        [sys.executable, str(SUITE), "--phase", phase, "--output", str(report_path)],
        cwd=str(SCRIPTS_ROOT),
        capture_output=True,
        text=True,
        timeout=600,
    )
    duration = time.monotonic() - start
    markdown = report_path.read_text(encoding="utf-8") if report_path.exists() else proc.stdout
    rows = agg.parse_report(markdown)
    # 以 case_id -> outcome 作為穩定度比對基準（忽略含隨機路徑的 evidence）。
    outcomes = {r.case: r.outcome.strip().lower() for r in rows}
    exit_codes = {r.case: r.actual_exit_code for r in rows}
    passed = sum(1 for r in rows if r.case_passed)
    return {
        "duration_sec": round(duration, 3),
        "suite_exit_code": proc.returncode,
        "cases_total": len(rows),
        "cases_passed": passed,
        "cases_failed": len(rows) - passed,
        "outcomes": outcomes,
        "exit_codes": exit_codes,
        "stderr_tail": proc.stderr.strip().splitlines()[-5:] if proc.stderr.strip() else [],
    }


def analyze(iterations: List[Dict]) -> Dict:
    """跨輪分析：找出 flaky case（outcome 在輪間翻轉）與時間漂移。"""
    all_cases = sorted({c for it in iterations for c in it["outcomes"]})
    flaky: Dict[str, List[str]] = {}
    for case in all_cases:
        seen = {it["outcomes"].get(case) for it in iterations if case in it["outcomes"]}
        seen.discard(None)
        if len(seen) > 1:
            flaky[case] = sorted(seen)
    durations = [it["duration_sec"] for it in iterations]
    pass_counts = {it["cases_passed"] for it in iterations}
    return {
        "iterations_run": len(iterations),
        "stable": len(flaky) == 0 and len(pass_counts) <= 1,
        "flaky_cases": flaky,
        "distinct_pass_counts": sorted(pass_counts),
        "duration_min_sec": min(durations) if durations else None,
        "duration_max_sec": max(durations) if durations else None,
        "duration_avg_sec": round(sum(durations) / len(durations), 3) if durations else None,
    }


def render_markdown(summary: Dict, iterations: List[Dict], analysis: Dict) -> str:
    lines = [
        "# Red-Team Marathon — 穩定度趨勢報告",
        "",
        "## Metadata",
        f"- Generated At: {summary['generated_at']}",
        "- Timezone: Asia/Taipei (+08:00)",
        f"- Phase: `{summary['phase']}`",
        f"- Iterations Requested: {summary['iterations_requested']}",
        f"- Iterations Run: {analysis['iterations_run']}",
        f"- Stop Reason: {summary['stop_reason']}",
        "",
        "## Verdict",
        "",
        f"- **Stable**: {'✅ YES — 每輪結果一致' if analysis['stable'] else '⚠️ NO — 偵測到不穩定，見下方 flaky/變動'}",
        f"- Distinct pass-counts seen: {analysis['distinct_pass_counts']}",
        f"- Duration (sec): min={analysis['duration_min_sec']} avg={analysis['duration_avg_sec']} max={analysis['duration_max_sec']}",
        "",
        "## Per-Iteration Trend",
        "",
        "| Iter | Duration (s) | Suite Exit | Cases | Pass | Fail |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for i, it in enumerate(iterations, 1):
        lines.append(
            f"| {i} | {it['duration_sec']} | {it['suite_exit_code']} | "
            f"{it['cases_total']} | {it['cases_passed']} | {it['cases_failed']} |"
        )
    lines += ["", "## Flaky Cases (outcome 在輪間翻轉)", ""]
    if analysis["flaky_cases"]:
        lines += ["| Case | Observed Outcomes |", "|---|---|"]
        for case, outcomes in analysis["flaky_cases"].items():
            lines.append(f"| `{case}` | {', '.join(outcomes)} |")
        lines.append("")
        lines.append("> ⚠️ flaky case = 紅隊套件存在非確定性，值得回來調查（隨機性、時序、暫存洩漏）。")
    else:
        lines.append("None — 所有 case 在每一輪的 outcome 都一致。")
    lines.append("")
    return "\n".join(lines) + "\n"


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Red-Team Marathon soak/stability experiment.")
    p.add_argument("--iterations", type=int, default=20, help="最大輪數 (default: 20)")
    p.add_argument("--max-minutes", type=float, default=60.0, help="最大總時長(分) (default: 60)")
    p.add_argument("--phase", choices=("static", "live", "prompt", "all"), default="static",
                   help="要跑的 suite phase (default: static，最快且純離線)")
    p.add_argument("--output-dir", default=str(REPO_ROOT / "artifacts" / "experiments" / "red_team_marathon"),
                   help="輸出目錄")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    out_dir = Path(args.output_dir)
    reports_dir = out_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    deadline = time.monotonic() + args.max_minutes * 60.0
    iterations: List[Dict] = []
    stop_reason = "completed-all-iterations"
    for i in range(1, args.iterations + 1):
        if time.monotonic() >= deadline:
            stop_reason = "hit-max-minutes"
            break
        report_path = reports_dir / f"iter_{i:03d}.md"
        print(f"[marathon] iteration {i}/{args.iterations} ...", flush=True)
        try:
            iterations.append(run_once(args.phase, report_path))
        except subprocess.TimeoutExpired:
            iterations.append({
                "duration_sec": 600.0, "suite_exit_code": -9999, "cases_total": 0,
                "cases_passed": 0, "cases_failed": 0, "outcomes": {}, "exit_codes": {},
                "stderr_tail": ["TIMEOUT"],
            })
            stop_reason = "iteration-timeout"
            break

    analysis = analyze(iterations)
    summary = {
        "generated_at": now_iso(),
        "phase": args.phase,
        "iterations_requested": args.iterations,
        "max_minutes": args.max_minutes,
        "stop_reason": stop_reason,
    }
    payload = {"summary": summary, "analysis": analysis, "iterations": iterations}
    (out_dir / "marathon_results.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "marathon_trend.md").write_text(
        render_markdown(summary, iterations, analysis), encoding="utf-8")

    print(f"[marathon] done: {analysis['iterations_run']} iterations, "
          f"stable={analysis['stable']}, stop={stop_reason}")
    print(f"[marathon] outputs: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
