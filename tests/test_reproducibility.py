# -*- coding: utf-8 -*-
"""回归测试：mock 语料的全量性与时间跨度。

锁定对象：提交前复核暴露的问题——`fetch_from_mock` 曾用"最后一条消息往前 N 天"
来施加 `--days` 窗口，而固定种子的语料实际跨 10.4 天，于是 `--days 10` 会静默
丢掉最早的 6 条（130 → 124），文档宣称的"130 条端到端"与实跑结果对不上，
且同一份数据在不同日期重跑可能得到不同条数。

修复后的约定：mock 源恒返回全量语料，`--days` 只对真实数据源（file / chatlog）生效。
"""
import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wechat_bridge import fetch_from_mock

CORPUS_SIZE = 130


class TestMockCorpusReproducibility(unittest.TestCase):
    def test_full_corpus_ignores_days(self):
        """带不带 days、days 多小，mock 都必须返回完整语料。"""
        self.assertEqual(len(fetch_from_mock("Elite20")), CORPUS_SIZE)
        self.assertEqual(len(fetch_from_mock("Elite20", days=1)), CORPUS_SIZE)
        self.assertEqual(len(fetch_from_mock("Elite20", days=10)), CORPUS_SIZE)

    def test_corpus_span_exceeds_ten_days(self):
        """语料时间跨度必须大于 10 天——这正是"按窗口截断会吞消息"的根因。"""
        msgs = fetch_from_mock("Elite20")
        stamps = [datetime.fromisoformat(m["timestamp"]) for m in msgs if m.get("timestamp")]
        self.assertEqual(len(stamps), CORPUS_SIZE)
        span_days = (max(stamps) - min(stamps)).total_seconds() / 86400
        self.assertGreater(span_days, 10.0, "语料跨度不足 10 天，天数窗口将不再具有区分度")

    def test_message_ids_unique_and_ordered(self):
        """消息 id 唯一、时间戳单调不减——下游去重与配对依赖这两个前提。"""
        msgs = fetch_from_mock("Elite20")
        ids = [m.get("msg_id") or m.get("id") for m in msgs]
        self.assertEqual(len(set(ids)), CORPUS_SIZE)
        stamps = [m["timestamp"] for m in msgs if m.get("timestamp")]
        self.assertEqual(stamps, sorted(stamps))


if __name__ == "__main__":
    unittest.main(verbosity=2)
