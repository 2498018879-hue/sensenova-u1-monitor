"""飞书交互卡片构建与发送。"""
import json


def build_card(title, tldr_lines, stats_line, doc_url=None):
    elements = []
    if stats_line:
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": stats_line}})
        elements.append({"tag": "hr"})
    for line in tldr_lines[:6]:
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": "• " + line}})
    if doc_url:
        elements.append({
            "tag": "action",
            "actions": [{
                "tag": "button",
                "text": {"tag": "plain_text", "content": "查看完整日报"},
                "type": "primary",
                "url": doc_url,
            }],
        })
    return {
        "config": {"wide_screen_mode": True},
        "header": {"title": {"tag": "plain_text", "content": title}, "template": "blue"},
        "elements": elements,
    }


def send_card(client, chat_id, card):
    r = client.request(
        "POST", "/im/v1/messages?receive_id_type=chat_id",
        data={
            "receive_id": chat_id,
            "msg_type": "interactive",
            "content": json.dumps(card, ensure_ascii=False),
        },
    )
    if r.get("code") != 0:
        raise RuntimeError(f"send card failed: {r}")
    return r["data"]["message_id"]


def send_text(client, chat_id, text):
    r = client.request(
        "POST", "/im/v1/messages?receive_id_type=chat_id",
        data={
            "receive_id": chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}, ensure_ascii=False),
        },
    )
    if r.get("code") != 0:
        raise RuntimeError(f"send text failed: {r}")
    return r["data"]["message_id"]
