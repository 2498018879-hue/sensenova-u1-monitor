# 舆情监控系统

每日自动监测 GitHub / Hacker News / Reddit / Hugging Face 上关于目标产品的舆情，
生成结构化日报，推送至飞书群（云文档 + 摘要卡片）。

## 特点

- **零依赖**：仅用 Python 标准库，无需 pip install
- **统一窗口**：昨日 08:00 → 今日 08:00（北京时间）
- **环比支持**：SQLite 存储历史声量/情感/指标，自动输出 vs 前一日
- **容错**：单平台失败不阻塞；飞书云文档失败自动降级文本消息
- **可配置**：监测对象（产品名/关键词/模型仓库/竞品）全部在 `config.json` 中维护，代码无硬编码

## 目录结构

```
sentiment-monitor/
├── README.md            # 本文件
├── DAILY_RUN.md         # 每日执行手册（定时任务按此操作）
├── config.example.json  # 监测配置模板（复制为 config.json 后填写真实监测对象）
├── config.json          # 真实监测配置（本地使用，勿提交）
├── .env                 # 飞书凭据（勿提交到任何仓库）
├── utils.py             # 窗口计算/HTTP/配置
├── db.py                # SQLite 历史库
├── stats.py             # 情感统计回写 CLI
├── collect.py           # ★ 采集入口
├── push.py              # ★ 飞书推送入口
├── collectors/          # 四平台采集器（github/hackernews/reddit/huggingface）
├── feishu/              # 飞书客户端/云文档导入/卡片
├── report/template.md   # 日报模板（7 段结构）
├── db/history.sqlite    # 历史数据（自动创建）
└── archive/YYYY-MM-DD/  # 每日归档：raw_items.jsonl + summary.json + report.md
```

## 快速使用

```bash
PY=/Users/luxiaolin/.workbuddy/binaries/python/versions/3.13.12/bin/python3
cd sentiment-monitor
cp config.example.json config.json   # 填入你的监测对象（产品名/关键词/模型仓库等）

$PY collect.py                            # 1. 采集
# 2. 分析 + 写报告（由 Agent 按 DAILY_RUN.md 完成）
$PY stats.py --date 2026-07-30 --pos 5 --neu 3 --neg 0   # 3. 回写情感
$PY push.py archive/2026-07-30/report.md  # 4. 推送飞书
```

## 配置

`.env`（本地填写，勿提交）：

```
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_CHAT_ID=oc_xxx
GITHUB_TOKEN=      # 可选，提升 GitHub API 限额（60/h → 5000/h）
```

飞书应用所需权限：`im:message`、`im:chat`、`docx:document`、`drive:drive`。

`config.json`（本地填写，勿提交）：把 `config.example.json` 复制为 `config.json`，
填入你的监测对象：`product`（产品展示名）、`keywords`（相关性主关键词）、
`github_search_query` / `hf_official_org` / `hf_models` / `strong_keywords` / `weak_keywords` 等。
调整监测词 / 子版 / 竞品无需动代码。

## 扩展

- **新增平台**：在 `collectors/` 加一个模块，实现 `collect(cfg, start, end) -> (items, snapshot, errors)`，
  在 `collect.py` 的 collectors 列表注册即可（X/Twitter 预留此插槽）。
- **调整监测词/子版/竞品**：直接改 `config.json`，无需动代码。
