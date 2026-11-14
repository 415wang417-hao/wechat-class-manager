# -*- coding: utf-8 -*-
"""单元测试：提交检测器（≥5 个提交事件 + 矩阵正确性 + 完整性告警）。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from classifier import classify_messages
from common import read_jsonl
from submission_detector import build_matrix, detect_submissions

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "sample_messages.jsonl")


class TestSubmissionDetector(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = read_jsonl(FIXTURE)
        clean_keys = ("msg_id", "timestamp", "sender", "type", "content", "media_ref", "reply_to")
        msgs = [{k: m[k] for k in clean_keys} for m in raw]
        cls.classified = classify_messages(msgs)
        cls.subs = detect_submissions(cls.classified)
        cls.result = build_matrix(cls.classified, cls.subs)

    def test_detects_at_least_5_submissions(self):
        print(f"\n[submission] 检测到 {len(self.subs)} 个提交事件")
        self.assertGreaterEqual(len(self.subs), 5, "验收标准：至少检测出 5 个提交事件")

    def test_submission_fields(self):
        for s in self.subs:
            self.assertRegex(s["challenge"], r"^C[1-8]$")
            self.assertTrue(2 <= len(s["student"]) <= 4, "学生姓名应为 2-4 个汉字")
            self.assertTrue(s["timestamp"])
            self.assertIn("has_ai_log", s["completeness"])

    def test_matrix_shape(self):
        matrix = self.result["matrix"]
        self.assertGreaterEqual(len(matrix), 10, "矩阵应覆盖至少 10 名活跃学生")
        for row in matrix.values():
            self.assertEqual(sorted(row.keys()), [f"C{i}" for i in range(1, 9)])

    def test_missing_and_alerts(self):
        self.assertGreater(self.result["totals"]["missing_count"], 0, "应存在未提交项")
        self.assertGreater(self.result["totals"]["alert_count"], 0, "应存在完整性告警（缺 AI 日志）")
        kinds = {a["type"] for a in self.result["alerts"]}
        self.assertIn("incomplete_submission", kinds)

    def test_wangyiran_c4_c5_c6(self):
        subs = {(s["student"], s["challenge"]) for s in self.subs}
        self.assertIn(("王艺燃", "C4"), subs)
        self.assertIn(("王艺燃", "C5"), subs)
        self.assertIn(("王艺燃", "C6"), subs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
