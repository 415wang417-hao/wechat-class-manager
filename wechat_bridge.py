# -*- coding: utf-8 -*-
"""Level 1 数据桥接（wechat-bridge）：把微信消息流变成 Agent 可消费的标准 JSONL。

三种数据源（--source）：
  mock    使用内置确定性模拟数据（20 名学生 × 10 天 × 约 150 条消息，含提交/问答/通知/闲聊）
  file    读取已有的 JSONL 文件（如从 chatlog / wechat-cli 导出的数据，先经 normalize）
  chatlog 调用本机安装的 sjzar/chatlog HTTP API（若可用），见 SETUP.md

用法：
  python wechat_bridge.py --group Elite20 --days 7 --output output/messages.jsonl
  python wechat_bridge.py --source file --input data/sample_output.jsonl --days 7 --output output/messages.jsonl
"""
import argparse
import json
import os
import sys

from common import BASE_DIR, normalize_message, read_jsonl, within_days, write_jsonl
from make_sample_data import generate_sample_messages


def fetch_from_mock(group, days=None):
    """mock 源返回内置确定性语料的全量消息（130 条，seed=20261105 固定）。

    刻意不对 mock 施加 --days 时间窗：合成语料本身就是一份固定的完整样本，
    若按"最后一条往前 N 天"裁剪，会因时间线随机抖动使跨度略超 N 天（实测 10.4 天），
    从而吞掉最早的几条消息，导致同一份数据在不同日期重跑得到不同条数（124 / 130 漂移），
    破坏可复现性。--days 只对真实数据源（file / chatlog）生效。
    """
    return generate_sample_messages(group=group)


def fetch_from_file(path, days):
    if not os.path.exists(path):
        raise FileNotFoundError(f"输入文件不存在: {path}")
    raw = read_jsonl(path)
    if raw:
        ref = raw[-1]["timestamp"]
        return [m for m in raw if within_days(m, days, reference=ref)]
    return []


def fetch_from_chatlog(group, days, base_url="http://127.0.0.1:5030"):
    """从本机 chatlog HTTP API 拉取群消息（需先安装并启动 sjzar/chatlog）。

    chatlog 是拿来主义参考来源之一：https://github.com/sjzar/chatlog
    这里只做最小对接——真实部署时按 chatlog 的 API 文档调整端点。
    """
    import urllib.request

    url = f"{base_url}/api/v1/chatlog?talker={group}&days={days}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(
            f"无法连接 chatlog API（{url}）。请确认已安装并启动 chatlog，"
            "或改用 --source mock / --source file。原始错误: {e}"
        ) from e
    return [normalize_message(m) for m in payload.get("messages", [])]


def main():
    ap = argparse.ArgumentParser(description="WeChat → 标准消息流桥接")
    ap.add_argument("--group", default="Elite20", help="群名称（chatlog/file 源按此过滤）")
    ap.add_argument("--days", type=int, default=7,
                    help="提取最近 N 天消息（仅对 file / chatlog 真实数据源生效；mock 恒返回全量确定性语料）")
    ap.add_argument("--source", choices=["mock", "file", "chatlog"], default="mock")
    ap.add_argument("--input", default=None, help="file 源的输入 JSONL 路径")
    ap.add_argument("--output", default=os.path.join(BASE_DIR, "output", "messages.jsonl"))
    args = ap.parse_args()

    if args.source == "mock":
        raw = fetch_from_mock(args.group, args.days)
    elif args.source == "file":
        raw = fetch_from_file(args.input or os.path.join(BASE_DIR, "data", "sample_output.jsonl"), args.days)
    else:
        raw = fetch_from_chatlog(args.group, args.days)

    messages = [normalize_message(m) for m in raw]
    write_jsonl(args.output, messages)
    print(f"[wechat-bridge] source={args.source} group={args.group} days={args.days}")
    print(f"[wechat-bridge] 共提取 {len(messages)} 条消息 → {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
