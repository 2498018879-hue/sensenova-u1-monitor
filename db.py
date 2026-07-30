"""SQLite 历史库：声量/情感/指标快照，支撑日报环比。"""
import os
import sqlite3

from utils import ROOT

DB_PATH = os.path.join(ROOT, "db", "history.sqlite")

SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_stats(
  date TEXT, platform TEXT, item_count INTEGER,
  pos INTEGER DEFAULT 0, neu INTEGER DEFAULT 0, neg INTEGER DEFAULT 0,
  PRIMARY KEY(date, platform)
);
CREATE TABLE IF NOT EXISTS repo_snapshot(
  date TEXT PRIMARY KEY, stars INTEGER, forks INTEGER,
  open_issues INTEGER, watchers INTEGER
);
CREATE TABLE IF NOT EXISTS hf_snapshot(
  date TEXT, model_id TEXT, downloads INTEGER, likes INTEGER,
  PRIMARY KEY(date, model_id)
);
CREATE TABLE IF NOT EXISTS items(
  id TEXT PRIMARY KEY, platform TEXT, url TEXT, date TEXT,
  title TEXT, sentiment TEXT, signal_type TEXT
);
"""


def conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.executescript(SCHEMA)
    return c


def seen_ids(c):
    return {r[0] for r in c.execute("SELECT id FROM items")}


def save_items(c, items, date):
    for it in items:
        c.execute(
            "INSERT OR IGNORE INTO items(id, platform, url, date, title) VALUES(?,?,?,?,?)",
            (it["id"], it["platform"], it["url"], date, (it.get("title") or "")[:300]),
        )


def save_counts(c, date, counts):
    for platform, n in counts.items():
        c.execute(
            "INSERT INTO daily_stats(date, platform, item_count) VALUES(?,?,?) "
            "ON CONFLICT(date, platform) DO UPDATE SET item_count=excluded.item_count",
            (date, platform, n),
        )


def save_repo_snapshot(c, date, snap):
    c.execute(
        "INSERT OR REPLACE INTO repo_snapshot VALUES(?,?,?,?,?)",
        (date, snap["stars"], snap["forks"], snap["open_issues"], snap["watchers"]),
    )


def save_hf_snapshot(c, date, model_id, downloads, likes):
    c.execute(
        "INSERT OR REPLACE INTO hf_snapshot VALUES(?,?,?,?)",
        (date, model_id, downloads, likes),
    )


def prev_day_summary(c, date):
    """取 date 之前最近一天的声量/情感/快照，供环比。"""
    row = c.execute(
        "SELECT DISTINCT date FROM daily_stats WHERE date < ? ORDER BY date DESC LIMIT 1", (date,)
    ).fetchone()
    if not row:
        return None
    prev = row[0]
    out = {"date": prev, "platforms": {}, "repo": None, "hf": {}}
    for p, n, pos, neu, neg in c.execute(
        "SELECT platform, item_count, pos, neu, neg FROM daily_stats WHERE date=?", (prev,)
    ):
        out["platforms"][p] = {"count": n, "pos": pos, "neu": neu, "neg": neg}
    r = c.execute(
        "SELECT stars, forks, open_issues, watchers FROM repo_snapshot WHERE date<=? ORDER BY date DESC LIMIT 1",
        (prev,),
    ).fetchone()
    if r:
        out["repo"] = {"stars": r[0], "forks": r[1], "open_issues": r[2], "watchers": r[3]}
    for m, d, l in c.execute(
        "SELECT model_id, downloads, likes FROM hf_snapshot WHERE date=?", (prev,)
    ):
        out["hf"][m] = {"downloads": d, "likes": l}
    return out
