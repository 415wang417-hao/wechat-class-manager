# -*- coding: utf-8 -*-
"""端到端流水线：bridge → classify → link → submission → qa → report。

一次运行产出全部交付物：
  output/messages.jsonl      标准化消息流
  output/linked.jsonl        分类 + 挑战关联后的富化消息流
  output/submissions.json    学生×挑战提交矩阵 + 告警
  output/qa_pairs.json       问答对
  output/weekly_report.md    自动周报

用法：
  python pipeline.py                      # 模拟数据全流程（mock 恒为全量 130 条确定性语料）
  python pipeline.py --days 7             # 只取最近 7 天（仅对真实数据源生效）
  python pipeline.py --source file --input data/sample_output.jsonl
"""
import argparse
import os
import sys

from challenge_linker import link_messages
from classifier import classify_messages
from common import BASE_DIR, load_config, read_jsonl, write_json, write_jsonl
from qa_extractor import extract_qa_pairs
from reporter import generate_report
from submission_detector import build_matrix
from wechat_bridge import fetch_from_file, fetch_from_mock
from make_sample_data import export as export_sample_data


def run(source="mock", days=10, input_path=None, out_dir=None):
    out_dir = out_dir or os.path.join(BASE_DIR, "output")
    os.makedirs(out_dir, exist_ok=True)

    # 0. 确保模拟数据存在
    sample_path = os.path.join(BASE_DIR, "data", "sample_output.jsonl")
    if not os.path.exists(sample_path):
        export_sample_data()

    # 1. 数据桥接（Layer 1）
    if source == "mock":
        raw = fetch_from_mock("Elite20", days)
    else:
        raw = fetch_from_file(input_path or sample_path, days)
    from common import normalize_message

    messages = [normalize_message(m) for m in raw]
    p_msgs = os.path.join(out_dir, "messages.jsonl")
    write_jsonl(p_msgs, messages)

    # 2. 消息分类（Layer 2）
    classified = classify_messages(messages)

    # 3. 挑战关联（Layer 2）
    cfg = load_config("challenges.json")
    valid = {c["id"] for c in cfg["challenges"]}
    enriched = []
    for m in link_messages(classified):
        e = dict(m)
        e["challenge_ref"] = [r for r in (e.get("challenge_ref") or []) if r in valid] or None
        enriched.append(e)
    p_linked = os.path.join(out_dir, "linked.jsonl")
    write_jsonl(p_linked, enriched)

    # 4. 提交追踪（Layer 3）
    sub_result = build_matrix(enriched)
    p_subs = os.path.join(out_dir, "submissions.json")
    write_json(p_subs, sub_result)

    # 5. Q&A 沉淀（Layer 3）
    qa_pairs = extract_qa_pairs(enriched)
    p_qa = os.path.join(out_dir, "qa_pairs.json")
    write_json(p_qa, qa_pairs)

    # 6. 周报（Layer 3）
    _, p_report = generate_report(p_linked, os.path.join(out_dir, "weekly_report.md"))

    # 摘要
    from collections import Counter

    dist = Counter(m["intent"] for m in enriched)
    days_label = "n/a（mock 全量确定性语料）" if source == "mock" else days
    print("=" * 60)
    print(f"[pipeline] source={source} days={days_label} messages={len(messages)}")
    print(f"[pipeline] intent 分布: {dict(dist.most_common())}")
    print(f"[pipeline] 提交事件 {sub_result['totals']['submission_events']} 个，"
          f"missing {sub_result['totals']['missing_count']}，alerts {sub_result['totals']['alert_count']}")
    print(f"[pipeline] QA 对 {len(qa_pairs)} 个")
    print("[pipeline] 产物:")
    for p in (p_msgs, p_linked, p_subs, p_qa, p_report):
        print(f"  - {os.path.relpath(p, BASE_DIR)}")
    print("=" * 60)
    return {"messages": len(messages), "submissions": sub_result, "qa": qa_pairs}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["mock", "file"], default="mock")
    ap.add_argument("--days", type=int, default=10)
    ap.add_argument("--input", default=None)
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()
    sys.exit(0 if run(args.source, args.days, args.input, args.out_dir) else 1)
