# -*- coding: utf-8 -*-
"""单元测试：挑战关联器 + 端到端流水线。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from challenge_linker import link_messages
from common import read_jsonl
from make_sample_data import build

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "sample_messages.jsonl")


class TestChallengeLinker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = read_jsonl(FIXTURE)
        clean_keys = ("msg_id", "timestamp", "sender", "type", "content", "media_ref", "reply_to")
        cls.msgs = [{k: m[k] for k in clean_keys} for m in cls.raw]
        cls.linked = link_messages(cls.msgs)

    def test_explicit_reference(self):
        m = next(x for x in self.linked if "C5 GitHub Repository" in x["content"])
        self.assertIn("C5", m["challenge_ref"] or [])

    def test_filename_reference(self):
        m = next(x for x in self.linked
                 if x.get("media_ref") and "王艺燃_C4_技能分享" in str(x["media_ref"]))
        self.assertIn("C4", m["challenge_ref"] or [])

    def test_keyword_reference(self):
        m = next(x for x in self.linked if "文献综述" in x["content"])
        self.assertIn("C2", m["challenge_ref"] or [])

    def test_linker_accuracy_on_gold(self):
        # 对每条有金标准的消息，判断 gold_refs 是否都被预测覆盖
        hit, total = 0, 0
        for raw_m, linked_m in zip(self.raw, self.linked):
            if raw_m["_gold_refs"]:
                total += 1
                pred = set(linked_m["challenge_ref"] or [])
                if set(raw_m["_gold_refs"]) <= pred:
                    hit += 1
        acc = hit / max(total, 1)
        print(f"\n[challenge-linker] 金标准覆盖率: {acc:.2%} ({hit}/{total})")
        self.assertGreaterEqual(acc, 0.75)


class TestPipelineEndToEnd(unittest.TestCase):
    def test_full_pipeline_produces_outputs(self):
        import tempfile

        import pipeline

        with tempfile.TemporaryDirectory() as tmp:
            result = pipeline.run(source="mock", days=30, out_dir=tmp)
            self.assertGreater(result["messages"], 100)
            self.assertGreaterEqual(result["submissions"]["totals"]["submission_events"], 5)
            self.assertGreaterEqual(len(result["qa"]), 10)
            for name in ("messages.jsonl", "linked.jsonl", "submissions.json", "qa_pairs.json", "weekly_report.md"):
                self.assertTrue(os.path.exists(os.path.join(tmp, name)), f"缺少产物 {name}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
