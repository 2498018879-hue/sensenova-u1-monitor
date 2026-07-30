"""日报推送入口：md 报告 → 飞书云文档 + 群摘要卡片。

用法: python3 push.py archive/2026-07-30/report.md
流程: 导入云文档 → 设为组织内可读 → 提取 TL;DR → 发卡片（带文档链接）。
云文档失败时降级：卡片无按钮 + 全文分段发文本消息。
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import load_env
from feishu.client import FeishuClient
from feishu import doc as fdoc
from feishu import card as fcard


def parse_report(md_path):
    with open(md_path, encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"^#\s+(.+)$", text, re.M)
    title = m.group(1).strip() if m else os.path.basename(md_path)

    tldr = []
    sec = re.search(r"##\s*1[.、]?\s*TL;DR(.*?)(?=\n##\s)", text, re.S)
    if sec:
        for line in sec.group(1).splitlines():
            line = line.strip().lstrip("*-•").strip()
            line = line.replace("\\*", "").replace("\\_", "_")
            if len(line) > 10:
                tldr.append(line[:180])
    return title, tldr, text


def main():
    if len(sys.argv) < 2:
        print("usage: python3 push.py <report.md>")
        sys.exit(1)
    md_path = sys.argv[1]
    load_env()
    chat_id = os.environ["FEISHU_CHAT_ID"]
    client = FeishuClient()

    title, tldr, full_text = parse_report(md_path)
    stats_line = f"**{title}**"

    doc_url = None
    try:
        doc_token, doc_url = fdoc.import_markdown(client, md_path, title)
        fdoc.make_tenant_readable(client, doc_token)
        print(f"[doc] created: {doc_url}")
    except Exception as e:  # noqa: BLE001
        print(f"[doc] FAILED ({e}), fallback to text messages")

    c = fcard.build_card(title, tldr, stats_line, doc_url)
    mid = fcard.send_card(client, chat_id, c)
    print(f"[card] sent: {mid}")

    if not doc_url:
        chunks, cur = [], ""
        for para in full_text.split("\n\n"):
            if len(cur) + len(para) > 3500:
                chunks.append(cur)
                cur = para
            else:
                cur = cur + "\n\n" + para if cur else para
        if cur:
            chunks.append(cur)
        for i, ch in enumerate(chunks, 1):
            fcard.send_text(client, chat_id, f"[{i}/{len(chunks)}]\n{ch}")
        print(f"[fallback] sent {len(chunks)} text chunks")


if __name__ == "__main__":
    main()
