# -*- coding: utf-8 -*-
"""Level 2 挑战关联器（challenge-linker）：把消息关联到具体挑战（C1–C8）。

两条路径：
  1. 显式引用：正文或文件名中出现 C4B / C6A 等挑战编号
  2. 语义线索：signal_keywords 匹配（翻译→C1、论文→C2、GitHub→C5……）

输出：每条消息增加 challenge_ref 字段（list[str] 或 None）。
"""
import re

from common import load_config

EXPLICIT_PAT = re.compile(r"\bC([1-8])([A-D])?\b")
FILE_PAT = re.compile(r"_C([1-8])([A-D])?_")

SIGNAL_KEYWORDS = {
    "C1": ["翻译", "translate", "本地化"],
    "C2": ["论文", "paper", "文献", "引用格式", "APA"],
    "C3": ["群内参与", "群内发言", "参与度"],
    "C4": ["技能分享", "skill", "SKILL.md", "技能包"],
    "C5": ["GitHub", "repo", "仓库", "开源", "commit", "PR"],
    "C6": ["Web App", "部署", "仪表盘", "dashboard", "上线"],
    "C7": ["公众号", "内容传播", "文章", "传播", "阅读量"],
    "C8": ["proposal", "真实项目", "AAR", "班级管理", "拿来说明"],
}


def _explicit_refs(text):
    refs = set()
    for m in EXPLICIT_PAT.finditer(text):
        cid = f"C{m.group(1)}"
        refs.add(cid)
    return refs


def _keyword_refs(text):
    refs = set()
    for cid, kws in SIGNAL_KEYWORDS.items():
        if any(kw in text for kw in kws):
            refs.add(cid)
    return refs


def link_one(msg):
    """返回该消息关联的挑战列表（可能为空）。"""
    refs = set()
    text = msg["content"] or ""
    refs |= _explicit_refs(text)
    media = str(msg.get("media_ref") or "")
    if media:
        fname = media.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        for m in FILE_PAT.finditer(fname):
            refs.add(f"C{m.group(1)}")
    refs |= _keyword_refs(text)
    return sorted(refs)


def link_messages(messages):
    """批量关联。每条消息增加 challenge_ref 字段。"""
    out = []
    for m in messages:
        enriched = dict(m)
        enriched["challenge_ref"] = link_one(m) or None
        out.append(enriched)
    return out


if __name__ == "__main__":
    import sys

    from common import read_jsonl, write_jsonl

    src = sys.argv[1] if len(sys.argv) > 1 else "output/messages.jsonl"
    dst = sys.argv[2] if len(sys.argv) > 2 else "output/linked.jsonl"
    cfg = load_config("challenges.json")
    valid = {c["id"] for c in cfg["challenges"]}
    result = []
    for m in read_jsonl(src):
        enriched = dict(m)
        refs = [r for r in link_one(m) if r in valid]
        enriched["challenge_ref"] = refs or None
        result.append(enriched)
    n = sum(1 for m in result if m["challenge_ref"])
    write_jsonl(dst, result)
    print(f"[challenge-linker] {n}/{len(result)} 条消息关联到具体挑战 → {dst}")
