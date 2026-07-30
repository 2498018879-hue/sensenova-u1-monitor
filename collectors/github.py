"""GitHub 采集：仓库指标快照 + 窗口内 issue/PR + 全站 issue 搜索。"""
import os

from utils import http_json


def _headers():
    h = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def collect(cfg, start, end):
    """返回 (items, snapshot)。start/end 为带时区 datetime。"""
    repo = cfg["github_repo"]
    items, snapshot, errors = [], None, []

    try:
        r = http_json(f"https://api.github.com/repos/{repo}", headers=_headers())
        snapshot = {
            "stars": r["stargazers_count"],
            "forks": r["forks_count"],
            "open_issues": r["open_issues_count"],
            "watchers": r["subscribers_count"],
            "pushed_at": r["pushed_at"],
        }
    except Exception as e:  # noqa: BLE001
        errors.append(f"repo snapshot: {e}")

    try:
        since = start.isoformat()
        issues = http_json(
            f"https://api.github.com/repos/{repo}/issues?state=all&since={since}&per_page=50",
            headers=_headers(),
        )
        for it in issues:
            items.append({
                "platform": "github",
                "id": f"gh-issue-{it['number']}",
                "url": it["html_url"],
                "title": it["title"],
                "text": (it.get("body") or "")[:2000],
                "author": it["user"]["login"],
                "created_at": it["created_at"],
                "metrics": {"comments": it.get("comments", 0)},
                "note": "new" if it["created_at"] >= since else "updated",
            })
    except Exception as e:  # noqa: BLE001
        errors.append(f"repo issues: {e}")

    try:
        q = 'in:title,body "' + cfg["github_search_query"] + '" created:>=' + start.strftime("%Y-%m-%d")
        import urllib.parse
        sr = http_json(
            "https://api.github.com/search/issues?q=" + urllib.parse.quote(q) + "&per_page=30",
            headers=_headers(),
        )
        for it in sr.get("items", []):
            iid = f"gh-search-{it['id']}"
            if any(x["id"] == f"gh-issue-{it.get('number')}" for x in items):
                continue
            items.append({
                "platform": "github",
                "id": iid,
                "url": it["html_url"],
                "title": it["title"],
                "text": (it.get("body") or "")[:2000],
                "author": it["user"]["login"],
                "created_at": it["created_at"],
                "metrics": {"comments": it.get("comments", 0)},
                "note": "global-search",
            })
    except Exception as e:  # noqa: BLE001
        errors.append(f"global search: {e}")

    return items, snapshot, errors
