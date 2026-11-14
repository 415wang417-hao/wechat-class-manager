# -*- coding: utf-8 -*-
"""共享工具：JSONL 读写、配置加载、消息规范化。

零第三方依赖，Python 3.9+ 标准库即可运行。
"""
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

VALID_TYPES = ("text", "image", "file", "voice", "link", "system")


def load_config(name):
    path = os.path.join(BASE_DIR, "config", name)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_jsonl(path):
    """读取 JSON Lines 文件，返回 list[dict]。"""
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}:{lineno} 不是合法 JSON: {e}") from e
    return records


def write_jsonl(path, records):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def write_json(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def normalize_message(raw):
    """把任意来源的原始消息规范化为标准 schema。

    必填: msg_id / timestamp / sender / type / content
    可选: media_ref / reply_to
    """
    msg = {
        "msg_id": str(raw["msg_id"]),
        "timestamp": str(raw["timestamp"]),
        "sender": {
            "wechat_id": str(raw.get("sender", {}).get("wechat_id", "unknown")),
            "nickname": str(raw.get("sender", {}).get("nickname", "unknown")),
        },
        "type": str(raw.get("type", "text")),
        "content": str(raw.get("content", "")),
        "media_ref": raw.get("media_ref"),
        "reply_to": raw.get("reply_to"),
    }
    if msg["type"] not in VALID_TYPES:
        msg["type"] = "text"
    return msg


def within_days(msg, days, reference=None):
    """判断消息时间戳是否在 reference 之前 days 天内。"""
    from datetime import datetime, timedelta

    def parse(ts):
        return datetime.fromisoformat(ts)

    ref = parse(reference) if reference else datetime.now()
    try:
        ts = parse(msg["timestamp"])
    except (ValueError, TypeError):
        return False
    return timedelta(0) <= (ref - ts) <= timedelta(days=days)
