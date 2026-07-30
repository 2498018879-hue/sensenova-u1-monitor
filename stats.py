"""情感统计写入 CLI（LLM 人工分类后调用）。

用法:
  python3 stats.py --date 2026-07-30 --pos 5 --neu 3 --neg 0
情感数写入 platform='ALL' 行，声量计数由 collect.py 自动写入。
"""
import argparse

import db


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--pos", type=int, required=True)
    ap.add_argument("--neu", type=int, required=True)
    ap.add_argument("--neg", type=int, required=True)
    args = ap.parse_args()
    c = db.conn()
    c.execute(
        "INSERT INTO daily_stats(date, platform, item_count, pos, neu, neg) "
        "VALUES(?, 'ALL', ?, ?, ?, ?) "
        "ON CONFLICT(date, platform) DO UPDATE SET pos=excluded.pos, neu=excluded.neu, neg=excluded.neg",
        (args.date, args.pos + args.neu + args.neg, args.pos, args.neu, args.neg),
    )
    c.commit()
    print(f"OK date={args.date} pos={args.pos} neu={args.neu} neg={args.neg}")


if __name__ == "__main__":
    main()
