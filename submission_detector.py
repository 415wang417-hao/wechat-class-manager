# -*- coding: utf-8 -*-
"""Level 2/3 提交检测器（submission-tracker）：从消息流中提取 Submission 记录。

输入：已分类/已关联的消息流（至少含 intent / challenge_ref）
输出：
  submissions.json —— 学生×挑战矩阵 + 每条 Submission 明细
  missing 列表 —— 该交没交的（学生 × 挑战）
  alerts 列表 —— deadline 前 3 天仍未提交的预警
"""
import re
from datetime import datetime, timedelta

from common import load_config

SUBMIT_FILE_PAT = re.compile(
    r"^(?P<student>[\u4e00-\u9fa5]{2,4})_C(?P<cid>[1-8])(?P<sub>[A-D])?_(?P<rest>.+)$"
)


def _filename_of(msg):
    media = str(msg.get("media_ref") or "")
    if not media:
        # 有的提交是纯文本说明（如 repo 链接），无附件
        return None
    return media.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]


def detect_submissions(messages):
    """扫描消息流，按（学生 × 挑战）聚合返回 Submission 记录。

    同一学生对同一挑战可能分多条消息提交（正文文件 + AI 日志），
    聚合后 completeness 才能反映真实完整性——这是 v0.2 修复的关键 bug：
    v0.1 按单文件告警，把「先交正文、后交 AI 日志」误报为缺日志。
    """
    cfg = load_config("challenges.json")
    challenge_ids = {c["id"] for c in cfg["challenges"]}
    grouped = {}  # (student, challenge) -> record
    for msg in messages:
        fname = _filename_of(msg)
        if not fname:
            continue
        m = SUBMIT_FILE_PAT.match(fname)
        if not m:
            continue
        cid = f"C{m.group('cid')}"
        if cid not in challenge_ids:
            continue
        key = (m.group("student"), cid)
        rec = grouped.setdefault(key, {
            "student": m.group("student"),
            "challenge": cid,
            "first_seen": msg["timestamp"],
            "last_seen": msg["timestamp"],
            "files": [],
            "source_msgs": [],
        })
        rec["last_seen"] = msg["timestamp"]
        rec["files"].append({"name": fname, "path": msg.get("media_ref")})
        rec["source_msgs"].append(msg["msg_id"])

    submissions = []
    for (student, cid), rec in sorted(grouped.items(), key=lambda kv: kv[0][1]):
        has_ai_log = any("AI日志" in f["name"] or "AI_LOG" in f["name"] for f in rec["files"])
        submissions.append({
            "student": student,
            "challenge": cid,
            "timestamp": rec["first_seen"],
            "last_seen": rec["last_seen"],
            "files": rec["files"],
            "status": "received",
            "completeness": {
                "has_ai_log": has_ai_log,
                "file_count": len(rec["files"]),
                "filename_matches_convention": True,
            },
            "source_msgs": rec["source_msgs"],
        })
    return submissions


def build_matrix(messages, submissions=None):
    """学生×挑战矩阵 + missing + alerts。"""
    group = load_config("group_config.json")
    chal = load_config("challenges.json")
    students = [s["name"] for s in group["students"]]
    challenge_ids = [c["id"] for c in chal["challenges"]]
    due = {c["id"]: c["due_date"] for c in chal["challenges"]}

    if submissions is None:
        submissions = detect_submissions(messages)

    # 只统计群里出现过（说话/提交过）的学生，避免矩阵全是全员
    active = {m["sender"]["nickname"] for m in messages}
    tracked = [s for s in students if s in active] or students

    done = {}
    for s in submissions:
        done[(s["student"], s["challenge"])] = s

    matrix, missing, alerts = {}, [], []
    ref_now = datetime.fromisoformat(messages[-1]["timestamp"]) if messages else datetime.now()
    # 只把「仍在进行窗口内」的挑战计入 missing：未截止，或截止后 7 天宽限期内
    grace = timedelta(days=7)
    active_challenges = [
        cid for cid in challenge_ids
        if datetime.fromisoformat(due[cid]) >= ref_now - grace
    ]
    for st in tracked:
        matrix[st] = {}
        for cid in challenge_ids:
            sub = done.get((st, cid))
            matrix[st][cid] = sub["status"] if sub else None
            if sub is None and cid in active_challenges:
                missing.append({"student": st, "challenge": cid, "due_date": due[cid]})

    # missing 中距截止 ≤ 3 天且未提交的 → deadline 预警
    for miss in missing:
        days_left = (datetime.fromisoformat(miss["due_date"]) - ref_now).days
        if 0 <= days_left <= 3:
            alerts.append({
                "type": "deadline_approaching",
                "student": miss["student"],
                "challenge": miss["challenge"],
                "days_left": days_left,
                "message": f"{miss['student']} 的 {miss['challenge']} 距截止仅剩 {days_left} 天且尚未提交",
            })

    # 提交了但缺 AI 日志 → 完整性告警
    for s in submissions:
        if not s["completeness"]["has_ai_log"]:
            alerts.append({
                "type": "incomplete_submission",
                "student": s["student"],
                "challenge": s["challenge"],
                "message": f"{s['student']} 的 {s['challenge']} 提交缺少 AI 日志",
            })

    return {
        "generated_from": len(messages),
        "tracked_students": len(tracked),
        "submissions": submissions,
        "matrix": matrix,
        "missing": missing,
        "alerts": alerts,
        "totals": {
            "submission_events": len(submissions),
            "missing_count": len(missing),
            "alert_count": len(alerts),
        },
    }


if __name__ == "__main__":
    import json
    import sys

    from common import read_jsonl, write_json

    src = sys.argv[1] if len(sys.argv) > 1 else "output/linked.jsonl"
    dst = sys.argv[2] if len(sys.argv) > 2 else "output/submissions.json"
    result = build_matrix(read_jsonl(src))
    write_json(dst, result)
    print(json.dumps(result["totals"], ensure_ascii=False))
    print(f"[submission-tracker] 矩阵 {len(result['matrix'])}×8 → {dst}")
