"""通用工具：时间窗口、HTTP 请求、环境变量、配置加载。仅用标准库。"""
import json
import os
import time
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone

BJT = timezone(timedelta(hours=8))
ROOT = os.path.dirname(os.path.abspath(__file__))


def load_env(path=None):
    """解析 .env 并注入 os.environ（不覆盖已有值）。"""
    path = path or os.path.join(ROOT, ".env")
    env = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    for k, v in env.items():
        os.environ.setdefault(k, v)
    return env


def load_config():
    with open(os.path.join(ROOT, "config.json"), encoding="utf-8") as f:
        return json.load(f)


def window(now=None):
    """统计窗口：最近一个北京时间 08:00 边界往前 24 小时。
    返回 (start_dt, end_dt, date_str)，date_str 为报告日期（=end 当天）。"""
    now = now or datetime.now(BJT)
    end = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if now < end:
        end -= timedelta(days=1)
    start = end - timedelta(days=1)
    return start, end, end.strftime("%Y-%m-%d")


def http_json(url, headers=None, timeout=30, retries=2, data=None, method=None):
    """GET/POST JSON，带重试。失败抛异常，由调用方捕获。"""
    h = {"User-Agent": "Mozilla/5.0 (compatible; sentiment-monitor/1.0)"}
    if headers:
        h.update(headers)
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, headers=h, data=body, method=method)
    last = None
    for i in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except Exception as e:  # noqa: BLE001
            last = e
            if i < retries:
                time.sleep(2 * (i + 1))
    raise last


def contains_keyword(text, cfg):
    """相关性初筛：命中主关键词，或弱相关词与上下文词共现（防撞名）。"""
    t = (text or "").lower()
    for kw in cfg["keywords"]:
        if kw.lower() in t:
            return True
    weak = cfg.get("weak_keywords", [])
    ctx = cfg.get("context_words", [])
    if weak and ctx:
        if any(w.lower() in t for w in weak) and any(c.lower() in t for c in ctx):
            return True
    return False
