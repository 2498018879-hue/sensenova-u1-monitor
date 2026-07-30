"""每日采集入口：四平台并汇总 → archive/日期/raw_items.jsonl + SQLite 快照 + 环比摘要。

用法: python3 collect.py            # 按最近 08:00 窗口采集
输出: archive/YYYY-MM-DD/raw_items.jsonl 与 summary.json，并打印摘要。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import db
from utils import ROOT, load_config, load_env, window
from collectors import github, hackernews, reddit, huggingface


def main():
    load_env()
    cfg = load_config()
    start, end, date = window()
    print(f"[window] {start:%Y-%m-%d %H:%M} -> {end:%Y-%m-%d %H:%M} BJT, report date {date}")

    c = db.conn()
    seen = db.seen_ids(c)
    all_items, all_errors = [], {}
    counts = {}

    collectors = [
        ("github", github),
        ("hackernews", hackernews),
        ("reddit", reddit),
        ("huggingface", huggingface),
    ]
    gh_snapshot, hf_snapshots = None, {}
    for name, mod in collectors:
        print(f"[collect] {name} ...", flush=True)
        try:
            items, snap, errors = mod.collect(cfg, start, end)
        except Exception as e:  # noqa: BLE001
            items, snap, errors = [], None, [f"collector crashed: {e}"]
        if name == "github" and snap:
            gh_snapshot = snap
        if name == "huggingface" and snap:
            hf_snapshots = snap
        fresh = [it for it in items if it["id"] not in seen]
        for it in fresh:
            it["seen_before"] = False
        counts[name] = len(fresh)
        all_items.extend(fresh)
        if errors:
            all_errors[name] = errors
        print(f"  -> {len(items)} items ({len(fresh)} new), {len(errors)} errors")

    out_dir = os.path.join(ROOT, "archive", date)
    os.makedirs(out_dir, exist_ok=True)
    raw_path = os.path.join(out_dir, "raw_items.jsonl")
    with open(raw_path, "w", encoding="utf-8") as f:
        for it in all_items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

    db.save_items(c, all_items, date)
    db.save_counts(c, date, counts)
    if gh_snapshot:
        db.save_repo_snapshot(c, date, gh_snapshot)
    for mid, s in hf_snapshots.items():
        if isinstance(s, dict) and "downloads" in s:
            db.save_hf_snapshot(c, date, mid, s["downloads"], s["likes"])
    prev = db.prev_day_summary(c, date)
    c.commit()

    summary = {
        "date": date,
        "window": [start.isoformat(), end.isoformat()],
        "counts": counts,
        "total_new_items": len(all_items),
        "github_snapshot": gh_snapshot,
        "hf_snapshots": hf_snapshots,
        "previous_day": prev,
        "errors": all_errors,
        "raw_items_file": raw_path,
    }
    summary_path = os.path.join(out_dir, "summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n[done] raw items: {raw_path}\n[done] summary:   {summary_path}")


if __name__ == "__main__":
    main()
