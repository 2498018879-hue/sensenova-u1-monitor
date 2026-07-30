"""Hugging Face 采集：模型指标快照 + 衍生模型搜索 + 社区讨论。"""
import urllib.parse

from utils import http_json


def collect(cfg, start, end):
    items, errors = [], []
    snapshots = {}

    for mid in cfg["hf_models"]:
        try:
            r = http_json(f"https://huggingface.co/api/models/{mid}")
            snapshots[mid] = {"downloads": r.get("downloads", 0), "likes": r.get("likes", 0)}
        except Exception as ex:  # noqa: BLE001
            errors.append(f"model {mid}: {ex}")

    seen = set()
    for q in cfg["hf_search_queries"]:
        try:
            r = http_json(
                "https://huggingface.co/api/models?search=" + urllib.parse.quote(q)
                + "&sort=lastModified&direction=-1&limit=30"
            )
            for m in r:
                mid = m["modelId"]
                if mid in seen:
                    continue
                seen.add(mid)
                items.append({
                    "platform": "huggingface",
                    "id": f"hf-model-{mid}",
                    "url": f"https://huggingface.co/{mid}",
                    "title": mid,
                    "text": "",
                    "author": mid.split("/")[0],
                    "created_at": m.get("lastModified"),
                    "metrics": {"downloads": m.get("downloads", 0), "likes": m.get("likes", 0)},
                    "note": f"search={q}" + ("; derived" if not mid.lower().startswith(cfg["hf_official_org"].lower() + "/") else "; official"),
                })
        except Exception as ex:  # noqa: BLE001
            errors.append(f"search {q}: {ex}")

    for mid in cfg["hf_models"]:
        try:
            r = http_json(f"https://huggingface.co/api/models/{mid}/discussions?p=0")
            for d in r.get("discussions", [])[:20]:
                did = f"hf-disc-{mid}-{d['num']}"
                created = d.get("createdAt", "")
                items.append({
                    "platform": "huggingface",
                    "id": did,
                    "url": f"https://huggingface.co/{mid}/discussions/{d['num']}",
                    "title": d.get("title", ""),
                    "text": "",
                    "author": (d.get("author") or {}).get("name"),
                    "created_at": created,
                    "metrics": {"status": d.get("status")},
                    "note": "discussion",
                })
        except Exception as ex:  # noqa: BLE001
            errors.append(f"discussions {mid}: {ex}")

    return items, snapshots, errors
