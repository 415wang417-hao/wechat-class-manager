# -*- coding: utf-8 -*-
"""单元测试：分类器准确率（金标准夹具，>70% 达标）。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from classifier import classify_messages
from common import read_jsonl

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "sample_messages.jsonl")


class TestClassifier(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = read_jsonl(FIXTURE)
        # 剥离金标准字段后再分类，避免信息泄漏
        clean_keys = ("msg_id", "timestamp", "sender", "type", "content", "media_ref", "reply_to")
        cls.input_msgs = [{k: m[k] for k in clean_keys} for m in cls.raw]
        cls.gold = [m["_label"] for m in cls.raw]
        cls.predicted = [m["intent"] for m in classify_messages(cls.input_msgs)]

    def test_fixture_loaded(self):
        self.assertGreater(len(self.raw), 100, "夹具应至少有 100 条消息")

    def test_overall_accuracy(self):
        correct = sum(1 for g, p in zip(self.gold, self.predicted) if g == p)
        acc = correct / len(self.gold)
        print(f"\n[classifier] 总体准确率: {acc:.2%} ({correct}/{len(self.gold)})")
        self.assertGreaterEqual(acc, 0.70, "验收标准：分类准确率 > 70%")

    def test_submission_recall(self):
        gold_sub = [i for i, g in enumerate(self.gold) if g == "submission"]
        hit = sum(1 for i in gold_sub if self.predicted[i] == "submission")
        recall = hit / max(len(gold_sub), 1)
        print(f"[classifier] 提交召回率: {recall:.2%} ({hit}/{len(gold_sub)})")
        self.assertGreaterEqual(recall, 0.90, "提交是最关键信号，召回率应 ≥ 90%")

    def test_question_recall(self):
        gold_q = [i for i, g in enumerate(self.gold) if g == "question"]
        hit = sum(1 for i in gold_q if self.predicted[i] == "question")
        recall = hit / max(len(gold_q), 1)
        print(f"[classifier] 提问召回率: {recall:.2%} ({hit}/{len(gold_q)})")
        self.assertGreaterEqual(recall, 0.80)

    def test_no_crash_on_edge_cases(self):
        edge = [
            {"msg_id": "e1", "timestamp": "2026-11-01T10:00:00+08:00",
             "sender": {"wechat_id": "x", "nickname": "路人"}, "type": "text",
             "content": "", "media_ref": None, "reply_to": None},
            {"msg_id": "e2", "timestamp": "2026-11-01T10:01:00+08:00",
             "sender": {"wechat_id": "x", "nickname": "路人"}, "type": "system",
             "content": "xxx 撤回了一条消息", "media_ref": None, "reply_to": "e1"},
        ]
        result = classify_messages(edge)
        self.assertEqual(len(result), 2)
        self.assertIn(result[0]["intent"], ("social", "question", "discussion", "resource"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
