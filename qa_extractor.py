# -*- coding: utf-8 -*-
"""Level 2 Q&A 提取器（qa-sink）：从消息流中沉淀问答对。

匹配策略（按优先级）：
  1. 回复链：answer 消息 reply_to 指向 question 消息
  2. 时间窗：question 之后 30 分钟内，其他同学的实质性回复（>10 字、非提问）

质量评分（0-1）：长度 + 含代码/链接 + 后续被感谢 → 简单可解释的启发式。
输出：qa_pairs.json（含 question / answer / 提问者 / 回答者 / topic_tags / quality_score）
"""
from datetime import datetime

from challenge_linker import link_one

THANKS_PAT = ("谢谢", "感谢", "学到了", "清楚了", "明白了", "原来如此")
MIN_ANSWER_LEN = 10


def _parse(ts):
    return datetime.fromisoformat(ts)


def _quality(answer_msg, follow_ups):
    score = 0.3
    content = answer_msg["content"]
    if len(content) >= 30:
        score += 0.2
    if len(content) >= 80:
        score += 0.1
    if "```" in content or "http" in content or "git " in content:
        score += 0.2
    if any(p in content for p in ("第一步", "第二步", "1.", "2.", "然后", "接着")):
        score += 0.1  # 结构化回答
    if any(t in f["content"] for t in THANKS_PAT for f in follow_ups):
        score += 0.2  # 被感谢 = 被验证有效
    return round(min(score, 1.0), 2)


def extract_qa_pairs(messages):
    by_id = {m["msg_id"]: m for m in messages}
    questions = [m for m in messages if m.get("intent") == "question"]
    answers = [m for m in messages if m.get("intent") == "answer"]

    # 建立 question_id -> [answer msgs] 映射
    ans_map = {}
    for a in answers:
        target = a.get("reply_to")
        if target and target in by_id and by_id[target].get("intent") == "question":
            ans_map.setdefault(target, []).append(a)

    def follow_ups_within(qid, minutes=30):
        q = by_id[qid]
        qt = _parse(q["timestamp"])
        out = []
        for m in messages:
            if m is q or m["sender"]["nickname"] == q["sender"]["nickname"]:
                continue
            dt = (_parse(m["timestamp"]) - qt).total_seconds() / 60
            if 0 <= dt <= minutes:
                out.append(m)
        return out

    pairs = []
    for q in questions:
        candidates = ans_map.get(q["msg_id"])
        method = "reply_chain"
        if not candidates:
            # 时间窗回退：30 分钟内第一个实质性回答
            method = "time_window"
            qt = _parse(q["timestamp"])
            for m in messages:
                if m is q or m["sender"]["nickname"] == q["sender"]["nickname"]:
                    continue
                if m.get("intent") in ("question", "announcement", "social", "system"):
                    continue
                dt = (_parse(m["timestamp"]) - qt).total_seconds() / 60
                if 0 <= dt <= 30 and len(m["content"]) >= MIN_ANSWER_LEN:
                    candidates = [m]
                    break
        if not candidates:
            continue
        best = max(candidates, key=lambda m: len(m["content"]))
        refs = link_one(q) or link_one(best)
        pairs.append({
            "question": q["content"],
            "answer": best["content"],
            "asked_by": q["sender"]["nickname"],
            "answered_by": best["sender"]["nickname"],
            "topic_tags": refs,
            "quality_score": _quality(best, follow_ups_within(q["msg_id"])),
            "match_method": method,
            "question_msg_id": q["msg_id"],
            "answer_msg_id": best["msg_id"],
            "timestamp": q["timestamp"],
        })

    pairs.sort(key=lambda p: -p["quality_score"])
    return pairs


if __name__ == "__main__":
    import sys

    from common import read_jsonl, write_json

    src = sys.argv[1] if len(sys.argv) > 1 else "output/linked.jsonl"
    dst = sys.argv[2] if len(sys.argv) > 2 else "output/qa_pairs.json"
    pairs = extract_qa_pairs(read_jsonl(src))
    write_json(dst, pairs)
    avg = sum(p["quality_score"] for p in pairs) / max(len(pairs), 1)
    print(f"[qa-sink] 提取 {len(pairs)} 个问答对（平均质量 {avg:.2f}）→ {dst}")
