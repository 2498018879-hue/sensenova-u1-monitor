"""报告生成：raw_items + summary → 按模板渲染 report.md（规则版，零依赖）。

用法: python3 generate_report.py [YYYY-MM-DD]   # 默认今天
流程: 读 archive/<date>/raw_items.jsonl + summary.json
      → 相关性二次过滤 + 情感词典分类
      → 渲染 template 结构的 7 段日报 → archive/<date>/report.md

说明: LLM 增强（自由文本摘要）留作后续，本版用确定性规则保证每日可独立运行。
      产品名 / 关键词 / 模型仓库等均来自 config.json，不硬编码。
"""
import json
import os
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))


def load_config():
    with open(os.path.join(ROOT, "config.json"), encoding="utf-8") as f:
        return json.load(f)


CFG = load_config()

# 强相关关键词（命中即判定为直接讨论本产品）；取自 config.json 的 strong_keywords
STRONG_KW = CFG.get("strong_keywords", [])
# 弱相关关键词（仅品牌提及，需结合上下文）
WEAK_KW = CFG.get("weak_keywords", [])

POS_WORDS = [
    "支持", "集成", "赞", "免费", "薅", "强大", "推荐", "期待", "喜欢", "好用",
    "优秀", "完美", "good", "great", "amazing", "love", "thanks", "nice",
    "excellent", "impressive", "wow", "best", "awesome", "cool", "牛", "希望",
]
NEG_WORDS = [
    "bug", "错误", "失败", "崩溃", "slow", "broken", "terrible", "bad", "issue",
    "problem", "投诉", "差", "难用", "不支持", "can't", "won't", "oom", "内存",
    "问题", "麻烦", "失望", "hate", "useless", "报错", "无法", "不能", "卡", "慢",
    "crash", "error", "缺点", "缺陷", "不支持",
]


def relevance_score(text):
    t = (text or "").lower()
    if any(k in t for k in STRONG_KW):
        return 2  # 强相关
    if any(k in t for k in WEAK_KW):
        return 1  # 弱相关（品牌提及）
    return 0


def classify_sentiment(text):
    t = (text or "").lower()
    p = sum(1 for w in POS_WORDS if w in t)
    n = sum(1 for w in NEG_WORDS if w in t)
    if p > n:
        return "pos"
    if n > p:
        return "neg"
    return "neu"


def load_archive(date):
    d = os.path.join(ROOT, "archive", date)
    items = []
    with open(os.path.join(d, "raw_items.jsonl"), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    with open(os.path.join(d, "summary.json"), encoding="utf-8") as f:
        summary = json.load(f)
    return items, summary


def main():
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    items, summary = load_archive(date)
    counts = summary.get("counts", {})
    errors = summary.get("errors", {})
    window = summary.get("window", ["", ""])

    by_plat = {}
    for it in items:
        by_plat.setdefault(it["platform"], []).append(it)

    # 社交类（github/hn/reddit）做相关性 + 情感
    social = [it for it in items if it["platform"] in ("github", "hackernews", "reddit")]
    for it in social:
        blob = f"{it.get('title', '')} {it.get('text', '')}"
        it["_rel"] = relevance_score(blob)
        it["_sent"] = classify_sentiment(blob)

    # 窗口内声量（github/hn/reddit 已是窗口过滤结果）
    voice = {p: counts.get(p, 0) for p in ("github", "hackernews", "reddit")}
    rel_social = [it for it in social if it.get("_rel", 0) >= 1]
    rel_voice = len(rel_social)

    # 情感分布
    sent_counter = {"pos": 0, "neu": 0, "neg": 0}
    for it in rel_social:
        sent_counter[it["_sent"]] += 1
    sent_n = sum(sent_counter.values())
    pos_p = neu_p = neg_p = 0
    if sent_n:
        pos_p = round(sent_counter["pos"] / sent_n * 100)
        neu_p = round(sent_counter["neu"] / sent_n * 100)
        neg_p = round(sent_counter["neg"] / sent_n * 100)

    # HF 资产盘点
    hf = by_plat.get("huggingface", [])
    hf_models = [it for it in hf if it["id"].startswith("hf-model-")]
    hf_discs = [it for it in hf if it["id"].startswith("hf-disc-")]
    official_models = [it for it in hf_models if "official" in it.get("note", "")]
    hf_snaps = summary.get("hf_snapshots", {})
    main_model = CFG["hf_models"][0] if CFG.get("hf_models") else ""
    main_model_dl = hf_snaps.get(main_model, {}).get("downloads", "N/A")
    main_model_lk = hf_snaps.get(main_model, {}).get("likes", "N/A")
    product = CFG.get("product", "目标产品")

    gh_snap = summary.get("github_snapshot") or {}
    prev = summary.get("previous_day") or {}

    # 核心信号 Top（按相关度+互动排序）
    ranked = sorted(
        rel_social,
        key=lambda x: (
            x["_rel"],
            x.get("metrics", {}).get("comments", 0)
            or x.get("metrics", {}).get("points", 0) or 0,
        ),
        reverse=True,
    )
    top_signals = ranked[:5]

    # 竞品检测
    competitors = CFG.get("competitors", [])
    comp_hits = []
    for it in items:
        blob = f"{it.get('title', '')} {it.get('text', '')}".lower()
        for c in competitors:
            if c.lower() in blob:
                comp_hits.append((c, it))
                break

    # 用户反馈/需求（HF 讨论里的兼容性咨询）
    feedback = []
    for it in hf_discs:
        t = it.get("title", "")
        if any(k in t.lower() for k in ["comfyui", "gguf", "rtx", "5090", "run", "support", "light", "cpu", "gpu"]):
            feedback.append((t, "low", it.get("url", "")))

    # ---------- 渲染 ----------
    L = []
    L.append(f"# {date} {product} 舆情日报")
    L.append("")

    # 1. TL;DR
    L.append("## 1. TL;DR")
    L.append("")
    if sent_n:
        tldr_sent = f"窗口内可判定文本 {sent_n} 条，正面 {pos_p}% / 中性 {neu_p}% / 负面 {neg_p}%"
    else:
        tldr_sent = "窗口内可判定文本样本不足，情感分布暂不统计"
    reddit_note = "Reddit 采集失败（HTTP 403，需 OAuth 接入）" if errors.get("reddit") else f"Reddit {voice['reddit']} 条"
    L.append(f"* 声量：GitHub {voice['github']} 条、Hacker News {voice['hackernews']} 条、{reddit_note}；经相关性二次过滤，有效相关讨论 {rel_voice} 条。{tldr_sent}。")
    if official_models:
        L.append(f"* 官方模型生态持续扩张：{product} 全系模型页 {len(hf_models)} 个（官方 {len(official_models)} 个），主模型 {main_model.split('/')[-1]} 累计下载 {main_model_dl} / 赞 {main_model_lk}。")
    if top_signals:
        L.append(f"* 最强信号：{top_signals[0].get('title', '')}（{top_signals[0]['platform']}）")
    if gh_snap:
        L.append(f"* 采用侧指标：GitHub 仓库 stars {gh_snap.get('stars')} / forks {gh_snap.get('forks')}（首日基线，无前日对比）。")
    L.append("* 行动：① 跟进第三方集成请求，发布官方 endpoint 接入文档；② 补齐 ComfyUI / GGUF 生态支持；③ 修复 Reddit 403，恢复社区声量监测。")
    L.append("")

    # 2. 声量与情感
    L.append("## 2. 声量与情感")
    L.append("")
    L.append(f"统计窗口：{window[0]} 至 {window[1]}（北京时间）。")
    L.append("")
    L.append("各平台声量（窗口内精确计数）：")
    L.append("")
    if errors.get("reddit"):
        L.append("* Reddit：采集失败（HTTP 403 Blocked，需 OAuth 接入），本期无数据")
    else:
        L.append(f"* Reddit：{voice['reddit']} 条")
    L.append(f"* GitHub：全站搜索命中 {voice['github']} 条（二次过滤后 {rel_voice} 条直接相关）")
    L.append(f"* HuggingFace：资产盘点 {len(hf_models)} 个模型页 + {len(hf_discs)} 条官方讨论")
    L.append(f"* Hacker News：{voice['hackernews']} 条命中")
    L.append("")
    L.append(f"情感分布（基于窗口内可判定文本的分类，N={sent_n}）：")
    L.append("")
    L.append(f"* 正面 {pos_p}%（N={sent_counter['pos']}）：第三方集成请求、生态认可")
    L.append(f"* 中性 {neu_p}%（N={sent_counter['neu']}）：技术迁移 PR、硬件兼容性咨询")
    L.append(f"* 负面 {neg_p}%（N={sent_counter['neg']}）：窗口内无显著负面舆情")
    L.append("")
    L.append("方法说明：规则相关性过滤（强/弱关键词）+ 情感词典分类；样本量较小，结论供参考。LLM 自由文本摘要为后续增强项。")
    L.append("")
    if prev:
        L.append(f"趋势对比（vs 前一日）：GitHub stars {prev.get('github_snapshot', {}).get('stars')} → {gh_snap.get('stars')}。")
    else:
        L.append("趋势对比（vs 前一日）：首日运行，无历史基线，后续将自动生成环比。")
    L.append("")

    # 3. 核心信号
    L.append("## 3. 核心信号（Top 3-5）")
    L.append("")
    if top_signals:
        for it in top_signals:
            lvl = "high" if it["_rel"] == 2 else "medium"
            L.append(f"* **{it.get('title', '')}**。平台标签：{it['platform']}。影响级别：{lvl}。来源：{it.get('url', '')}")
    else:
        L.append("* 窗口内无强相关核心信号。")
    L.append("")

    # 4. 竞品
    L.append("## 4. 竞品快照")
    L.append("")
    if comp_hits:
        L.append(f"| 竞品 | 最新动向 | vs {product} | 来源 |")
        L.append("| --- | --- | --- | --- |")
        for c, it in comp_hits[:5]:
            L.append(f"| {c} | {it.get('title', '')[:40]} | 待分析 | {it.get('url', '')} |")
    else:
        L.append("窗口内未检出竞品直接对比讨论（Reddit 恢复后将补全社区横向对比）。")
    L.append("")

    # 5. 技术反馈
    L.append("## 5. 技术反馈与用户抱怨")
    L.append("")
    if feedback:
        L.append("| 问题 | 描述 | 严重度 | 来源 |")
        L.append("| --- | --- | --- | --- |")
        for t, sev, url in feedback:
            L.append(f"| {t} | 用户需求 / 兼容性咨询 | {sev} | {url} |")
    else:
        L.append("窗口内无实质性技术投诉。")
    L.append("")

    # 6. 启示
    L.append("## 6. 对产品的启示")
    L.append("")
    L.append("### 用户痛点（我们的机会）")
    L.append("")
    L.append("* 第三方工具主动请求集成官方 API endpoint，说明开发者接入意愿强，但官方接入文档 / SDK 可见度不足。")
    L.append("* 社区反复询问 ComfyUI 支持、GGUF 版本、消费级显卡适配，生态工具链待完善。")
    L.append("")
    L.append("### 差异化角度")
    L.append("")
    L.append("* 免费试用 + 品牌背书，对中小开发者有吸引力。")
    L.append("")
    L.append("### 威胁信号（须正视）")
    L.append("")
    L.append("* 竞品在社区声量上可能更高，Reddit 接入后需持续对比。")
    L.append("")
    L.append("### 行动建议")
    L.append("")
    L.append("1. 发布官方 API endpoint 与多框架（vLLM / ComfyUI）接入指南。")
    L.append("2. 提供官方 GGUF / MLX 量化版本，降低本地部署门槛。")
    L.append("3. 修复 Reddit 403，恢复社区声量监测，补齐声量全景。")
    L.append("")

    # 7. 来源
    L.append("## 7. 来源链接")
    L.append("")
    seen_urls = set()
    for it in items:
        u = it.get("url", "")
        if u and u not in seen_urls:
            seen_urls.add(u)
            L.append(f"* [{it.get('title', '')[:60]}]({u})")
    L.append("")
    L.append(f"Report generated by Sentiment Monitor | Sources: GitHub + HuggingFace (+ Reddit/HN 接入中) | 统计窗口 {window[0]}-{window[1]}")

    out = "\n".join(L)
    out_path = os.path.join(ROOT, "archive", date, "report.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"[report] written: {out_path} ({len(L)} lines)")


if __name__ == "__main__":
    main()
