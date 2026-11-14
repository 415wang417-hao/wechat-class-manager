# -*- coding: utf-8 -*-
"""Level 3 报告引擎（class-report）：自动生成班级周报（Markdown）。

承接 C8 方案 Layer 3 的 report skill：输出可直接发群 / 转公众号。
"""
import sys
from collections import Counter
from datetime import datetime

from common import load_config, read_jsonl, write_json
from qa_extractor import extract_qa_pairs
from submission_detector import build_matrix


def generate_report(messages, out_path="output/weekly_report.md"):
    classified = read_jsonl(messages) if isinstance(messages, str) else messages
    sub_result = build_matrix(classified)
    qa_pairs = extract_qa_pairs(classified)

    n = len(classified)
    intents = Counter(m.get("intent", "unknown") for m in classified)
    group_cfg = load_config("group_config.json")
    teacher_ids = {t["wechat_id"] for t in group_cfg["teachers"]}
    active = Counter(
        m["sender"]["nickname"] for m in classified
        if m["type"] != "system" and m["sender"]["wechat_id"] not in teacher_ids
    )
    end_time = classified[-1]["timestamp"] if classified else "-"
    start_time = classified[0]["timestamp"] if classified else "-"

    lines = []
    lines.append(f"# Elite20 班级周报")
    lines.append("")
    lines.append(f"- 数据窗口：{start_time} ~ {end_time}（共 {n} 条消息）")
    lines.append(f"- 活跃学生：{len(active)} 人")
    lines.append("")
    lines.append("## 一、消息构成")
    for k, v in intents.most_common():
        lines.append(f"- {k}: {v} 条（{v / max(n, 1) * 100:.0f}%）")
    lines.append("")
    lines.append("## 二、提交情况")
    totals = sub_result["totals"]
    lines.append(f"- 本期共检测到 **{totals['submission_events']}** 次提交事件")
    lines.append(f"- 待交：{totals['missing_count']} 项；告警：{totals['alert_count']} 条")
    if sub_result["alerts"]:
        lines.append("")
        lines.append("### 需要关注")
        for a in sub_result["alerts"][:10]:
            lines.append(f"- ⚠️ {a['message']}")
    lines.append("")
    lines.append("## 三、最活跃学生 Top 5")
    for name, cnt in active.most_common(5):
        lines.append(f"- {name}：{cnt} 条发言")
    lines.append("")
    lines.append("## 四、高质量 Q&A Top 5")
    for p in qa_pairs[:5]:
        tags = "/".join(p["topic_tags"]) if p["topic_tags"] else "通用"
        lines.append(f"- **Q**（{p['asked_by']}，{tags}）：{p['question'][:60]}")
        lines.append(f"  **A**（{p['answered_by']}，质量 {p['quality_score']}）：{p['answer'][:80]}")
    lines.append("")
    lines.append("---")
    lines.append(f"*由 wechat-class-manager 自动生成 · {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

    report = "\n".join(lines)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    return report, out_path


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "output/linked.jsonl"
    dst = sys.argv[2] if len(sys.argv) > 2 else "output/weekly_report.md"
    _, path = generate_report(src, dst)
    print(f"[class-report] 周报已生成 → {path}")
