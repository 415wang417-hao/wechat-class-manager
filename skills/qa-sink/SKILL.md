# Skill: qa-sink（Q&A 沉淀）

## 触发词
问答沉淀、群里的好问题、FAQ、qa pairs、知识沉淀

## 用途
从消息流提取问答对，建立课程 FAQ 数据底座（Layer 3）。

## 输入 / 输出
- 输入：已分类的消息流（JSONL）
- 输出：`output/qa_pairs.json`，符合 `schemas/qa_pair.schema.json`，按质量分降序

## 匹配策略
1. 回复链优先：answer 消息 `reply_to` 指向 question
2. 时间窗回退：question 后 30 分钟内首个实质性回答

## 质量评分（0-1 启发式）
长度 + 含代码/链接 + 结构化（分步骤）+ 被提问者感谢

## 依赖
- Python 3.9+，零第三方依赖

## 调用示例
```bash
python qa_extractor.py output/linked.jsonl output/qa_pairs.json
```
