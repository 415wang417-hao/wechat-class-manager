# -*- coding: utf-8 -*-
"""单元测试：Q&A 提取器（≥10 个问答对 + 质量分有效 + 主题标签）。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from challenge_linker import link_messages
from classifier import classify_messages
from common import read_jsonl
from qa_extractor import extract_qa_pairs

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "sample_messages.jsonl")


class TestQAExtractor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = read_jsonl(FIXTURE)
        clean_keys = ("msg_id", "timestamp", "sender", "type", "content", "media_ref", "reply_to")
        msgs = [{k: m[k] for k in clean_keys} for m in raw]
        cls.enriched = link_messages(classify_messages(msgs))
        cls.pairs = extract_qa_pairs(cls.enriched)

    def test_at_least_10_pairs(self):
        print(f"\n[qa-sink] 提取到 {len(self.pairs)} 个问答对")
        self.assertGreaterEqual(len(self.pairs), 10, "验收标准：至少 10 个有意义的 Q&A 对")

    def test_pair_structure(self):
        for p in self.pairs:
            self.assertTrue(p["question"].strip())
            self.assertTrue(p["answer"].strip())
            self.assertNotEqual(p["asked_by"], p["answered_by"], "自问自答不成立")
            self.assertTrue(0 <= p["quality_score"] <= 1)

    def test_reply_chain_is_primary(self):
        chained = sum(1 for p in self.pairs if p["match_method"] == "reply_chain")
        print(f"[qa-sink] 回复链匹配 {chained}/{len(self.pairs)}")
        self.assertGreater(chained, len(self.pairs) * 0.5, "回复链应是主要匹配方式")

    def test_quality_score_ranking(self):
        scores = [p["quality_score"] for p in self.pairs]
        self.assertEqual(scores, sorted(scores, reverse=True), "结果应按质量分降序")

    def test_topic_tags_present(self):
        tagged = sum(1 for p in self.pairs if p["topic_tags"])
        print(f"[qa-sink] 带主题标签 {tagged}/{len(self.pairs)}")
        self.assertGreater(tagged, len(self.pairs) * 0.5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
