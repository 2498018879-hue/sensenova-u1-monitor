"""Reddit 采集：目标子版新帖 + 全站搜索（公开 JSON 接口，限速 1 req/s）。"""
import time
import urllib.parse

from utils import http_json, contains_keyword

UA = {"User-Agent": "python:sentiment-monitor:v1.0 (research bot)"}


def _post_to_item(p, note):
    d = p["data"]
    return {
        "platform": "reddit",
        "id": f"rd-{d['id']}",
        "url": "https://www.reddit.com" + d.get("permalink", ""),
        "title": d.get("title", ""),
        "text": (d.get("selftext") or "")[:2000],
        "author": d.get("author"),
        "created_at": d.get("created_utc"),
        "metrics": {"score": d.get("score"), "num_comments": d.get("num_comments")},
        "note": note,
    }


def collect(cfg, start, end):
    items, errors = [], []
    s, e = start.timestamp(), end.timestamp()
    seen = set()

    for sub in cfg["reddit_subreddits"]:
        try:
            r = http_json(f"https://www.reddit.com/r/{sub}/new.json?limit=50", headers=UA, timeout=10, retries=1)
            for p in r["data"]["children"]:
                d = p["data"]
                if not (s <= d.get("created_utc", 0) < e):
                    continue
                if not contains_keyword(d.get("title", "") + " " + (d.get("selftext") or ""), cfg):
                    continue
                it = _post_to_item(p, f"r/{sub}")
                if it["id"] not in seen:
                    seen.add(it["id"])
                    items.append(it)
        except Exception as ex:  # noqa: BLE001
            errors.append(f"r/{sub}: {ex}")
        time.sleep(1.1)

    for q in cfg["reddit_search_queries"]:
        try:
            url = "https://www.reddit.com/search.json?q=" + urllib.parse.quote(q) + "&sort=new&limit=50&t=week"
            r = http_json(url, headers=UA, timeout=10, retries=1)
            for p in r["data"]["children"]:
                d = p["data"]
                if not (s <= d.get("created_utc", 0) < e):
                    continue
                it = _post_to_item(p, f"search={q}")
                if it["id"] not in seen:
                    seen.add(it["id"])
                    items.append(it)
        except Exception as ex:  # noqa: BLE001
            errors.append(f"search {q}: {ex}")
        time.sleep(1.1)

    return items, {"subreddits_scanned": len(cfg["reddit_subreddits"])}, errors
