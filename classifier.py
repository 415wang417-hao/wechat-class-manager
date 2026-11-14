# -*- coding: utf-8 -*-
"""Level 2 消息分类器（msg-classifier）：为每条消息打意图标签。

标签体系（与 C8 方案一致）：
  submission  挑战提交：文件 + 命名规范匹配
  question    提问：问号 / 怎么 / 为什么 / 请问 等
  answer      回答：回复了一条 question 消息
  announcement 通知公告：老师发送 / @全体 / deadline
  discussion  讨论：围绕挑战或课程话题
  resource    资源分享：链接、文件推荐
  social      日常闲聊：兜底

实现方式：规则引擎（Bronze 级，零依赖、可离线、可解释）。
预留 LLM 精分类接口（Silver/Gold 级）：classify_with_llm()。
"""
import re

from common import load_config

# ---- 规则字典（可按课程语料持续扩充） ----
QUESTION_PAT = re.compile(
    r"[?？]|怎么|如何|为什么|为啥|请问|请教|求助|有没有人|哪位|不会弄|搞不定|报错|卡在"
)
ANNOUNCE_PAT = re.compile(r"@全体|@所有人|通知|公告|deadline|截止| ddl|DDL")
RESOURCE_PAT = re.compile(r"https?://|推荐|分享一个|转一个|链接在这|好文|干货")
SOCIAL_PAT = re.compile(r"哈哈|嘿嘿|早|晚安|吃饭|周末|谢谢|辛苦|鼓掌|🎉|👍|牛")
# 提交命名规范：姓名_C8_ 说明.md / 姓名_C5_ AI日志.md 等
SUBMIT_FILE_PAT = re.compile(r"^[\u4e00-\u9fa5]{2,4}_C[1-8][A-Za-z]?_.+\.[a-zA-Z0-9]+$")


def _looks_like_submission(msg):
    if msg["type"] == "file" and msg.get("media_ref"):
        name = str(msg["media_ref"]).rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        return bool(SUBMIT_FILE_PAT.match(name)), 0.95
    m = re.search(r"提交.*(C[1-8][A-Za-z]?|\S+日)", msg["content"])
    if m and msg["type"] in ("file", "text") and msg.get("media_ref"):
        return True, 0.7
    return False, 0.0


def classify_one(msg, teacher_ids, msg_index):
    """对单条消息分类。msg_index: {msg_id: msg} 供回复链判断。"""
    if msg["type"] == "system":
        return "system", 1.0

    is_sub, conf = _looks_like_submission(msg)
    if is_sub:
        return "submission", conf

    sender_id = msg["sender"]["wechat_id"]
    is_teacher = sender_id in teacher_ids
    if is_teacher and ANNOUNCE_PAT.search(msg["content"]):
        return "announcement", 0.95
    if is_teacher and msg["type"] in ("text", "link") and len(msg["content"]) > 30:
        # 老师发的长内容默认视为通知（本课程语境下的合理先验）
        return "announcement", 0.75
    if "@全体" in msg["content"] or "@所有人" in msg["content"]:
        return "announcement", 0.9

    # 回复了一条 question → answer
    reply_to = msg.get("reply_to")
    if reply_to:
        target = msg_index.get(reply_to)
        if target is not None:
            t_intent, _ = classify_one_simple(target, teacher_ids, msg_index, depth=1)
            if t_intent == "question":
                return "answer", 0.85

    if QUESTION_PAT.search(msg["content"]):
        return "question", 0.85

    if RESOURCE_PAT.search(msg["content"]) and msg["type"] in ("link", "file", "text"):
        return "resource", 0.8

    if re.search(r"C[1-8][A-Za-z]?\b|课程|挑战|proposal|AI日志|拿来说明|GitHub|微信群", msg["content"]):
        return "discussion", 0.6

    if SOCIAL_PAT.search(msg["content"]) and len(msg["content"]) < 40:
        return "social", 0.6

    return "social", 0.4


def classify_one_simple(msg, teacher_ids, msg_index, depth=0):
    if depth > 2:
        return "social", 0.3
    return classify_one(msg, teacher_ids, msg_index) if depth == 0 else _shallow(msg)


def _shallow(msg):
    if QUESTION_PAT.search(msg["content"]):
        return "question", 0.7
    return "social", 0.3


def classify_messages(messages):
    """批量分类。返回新列表，每条消息增加 intent / confidence 字段。"""
    cfg = load_config("group_config.json")
    teacher_ids = {t["wechat_id"] for t in cfg["teachers"]}
    msg_index = {m["msg_id"]: m for m in messages}
    out = []
    for m in messages:
        intent, conf = classify_one(m, teacher_ids, msg_index)
        enriched = dict(m)
        enriched["intent"] = intent
        enriched["confidence"] = conf
        out.append(enriched)
    return out


def classify_with_llm(messages, call_llm):
    """Silver/Gold 级扩展点：规则预筛置信度 < 0.7 的消息交给 LLM 精分类。

    call_llm: callable(content, context) -> (label, confidence)
    规则先兜底，LLM 只处理模糊样本——混合分类（Gold 方案）。
    """
    cfg = load_config("group_config.json")
    teacher_ids = {t["wechat_id"] for t in cfg["teachers"]}
    msg_index = {m["msg_id"]: m for m in messages}
    out = []
    for m in messages:
        intent, conf = classify_one(m, teacher_ids, msg_index)
        if conf < 0.7 and call_llm:
            try:
                intent, conf = call_llm(m["content"], m)
            except Exception:  # noqa: BLE001
                pass  # LLM 失败时回退到规则结果
        enriched = dict(m)
        enriched["intent"] = intent
        enriched["confidence"] = conf
        out.append(enriched)
    return out


def _summary(stats):
    return ", ".join(f"{k}={v}" for k, v in sorted(stats.items()))


if __name__ == "__main__":
    import sys

    from common import read_jsonl, write_jsonl

    src = sys.argv[1] if len(sys.argv) > 1 else "output/messages.jsonl"
    dst = sys.argv[2] if len(sys.argv) > 2 else "output/classified.jsonl"
    result = classify_messages(read_jsonl(src))
    write_jsonl(dst, result)
    stats = {}
    for m in result:
        stats[m["intent"]] = stats.get(m["intent"], 0) + 1
    print(f"[msg-classifier] {len(result)} 条 → {dst}")
    print(f"[msg-classifier] 分布: {_summary(stats)}")
