"""Hacker News 采集：Algolia 搜索 API，按时间窗口过滤。"""
import urllib.parse

from utils import http_json


def collect(cfg, start, end):
    items, errors = [], []
    s, e = int(start.timestamp()), int(end.timestamp())
    seen = set()
    for q in cfg["hn_queries"]:
        try:
            url = (
                "https://hn.algolia.com/api/v1/search_by_date?query="
                + urllib.parse.quote(q)
                + f"&tags=(story,comment)&numericFilters=created_at_i>={s},created_at_i<{e}&hitsPerPage=50"
            )
            r = http_json(url)
            for hit in r.get("hits", []):
                hid = f"hn-{hit['objectID']}"
                if hid in seen:
                    continue
                seen.add(hid)
                items.append({
                    "platform": "hackernews",
                    "id": hid,
                    "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}",
                    "title": hit.get("title") or hit.get("story_title") or "",
                    "text": (hit.get("comment_text") or hit.get("story_text") or "")[:2000],
                    "author": hit.get("author"),
                    "created_at": hit.get("created_at"),
                    "metrics": {"points": hit.get("points"), "num_comments": hit.get("num_comments")},
                    "note": f"query={q}",
                })
        except Exception as ex:  # noqa: BLE001
            errors.append(f"hn query {q}: {ex}")
    return items, None, errors
