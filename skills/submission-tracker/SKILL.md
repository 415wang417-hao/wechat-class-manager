# Skill: submission-tracker（提交追踪）

## 触发词
提交追踪、谁没交、缺交名单、提交矩阵、催交、deadline 预警

## 用途
从消息流提取学生×挑战提交矩阵，产出 missing 列表与完整性告警（Layer 3）。

## 输入 / 输出
- 输入：已分类的消息流（JSONL）+ `config/challenges.json`
- 输出：`output/submissions.json`（矩阵 + submissions + missing + alerts），符合 `schemas/submission.schema.json`

## 依赖
- Python 3.9+，零第三方依赖

## 调用示例
```bash
python submission_detector.py output/linked.jsonl output/submissions.json
```

## 告警规则
1. `deadline_approaching`：距截止 ≤3 天且未提交
2. `incomplete_submission`：已提交但缺 AI 日志（按学生×挑战聚合判定，不按单文件）
