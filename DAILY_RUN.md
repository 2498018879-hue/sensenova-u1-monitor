# 每日运行手册（供定时任务 Agent 执行）

项目根目录：`sentiment-monitor/`
Python：`/Users/luxiaolin/.workbuddy/binaries/python/versions/3.13.12/bin/python3`

## 执行步骤

### 第 1 步：采集

```bash
cd sentiment-monitor
python3 collect.py
```

产出 `archive/{DATE}/raw_items.jsonl`（原始条目）和 `summary.json`（声量计数、GitHub/HF 指标快照、前一日环比数据、采集错误清单）。

### 第 2 步：分析（由 Agent 完成，无需外部 API）

读取 `raw_items.jsonl` 与 `summary.json`，执行：

1. **相关性过滤**：逐条判断是否真实指向监测目标产品。
   剔除撞名（其他同名产品）、无关噪声。HF discussions 未按窗口过滤，需剔除窗口外旧帖。
2. **情感分类**：对可判定文本标注 pos/neu/neg，记录样本量 N。
3. **信号提取**：官方动态 / 竞品动向（对照 config.json 的 competitors 清单）/ 用户实测 / 技术抱怨 / 学术生态，标注 high/medium/low 影响级别。

### 第 3 步：写报告

按 `report/template.md` 结构生成 `archive/{DATE}/report.md`：

- 文件名与一级标题：`{DATE} 舆情日报`
- 每个结论必须挂来源 URL；无数据的平台明确写 "0 命中"
- 环比数据取 `summary.json` 的 `previous_day` 字段（首日无环比则注明"首期无对比基线"）
- 采集出错的平台在"方法说明"中标注"该平台采集失败"

### 第 4 步：回写情感统计（供明日环比）

```bash
python3 stats.py --date {DATE} --pos {N} --neu {N} --neg {N}
```

### 第 5 步：推送飞书

```bash
python3 push.py archive/{DATE}/report.md
```

自动完成：md 导入云文档 → 设组织内可读 → 群里发摘要卡片（TL;DR + 完整日报按钮）。
云文档失败时自动降级为分段文本消息，不阻塞。

## 容错原则

- 单平台采集失败不阻塞，报告中如实标注
- 推送失败可手动重跑 `push.py`（报告文件已在 archive 中归档）
- 全流程幂等：同一天重复运行会覆盖当天数据，不会产生重复记录
