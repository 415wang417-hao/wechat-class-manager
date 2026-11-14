# Skill: msg-classifier（消息分类）

## 触发词
消息分类、意图识别、哪条是提问、找出提交消息、classify

## 用途
为每条消息打意图标签：submission / question / answer / announcement / discussion / resource / social。

## 输入 / 输出
- 输入：符合 message.schema.json 的 JSONL
- 输出：每条消息增加 `intent` / `confidence` 字段

## 依赖
- Python 3.9+，零第三方依赖（规则引擎，Bronze 级）
- `classify_with_llm(messages, call_llm)` 预留混合分类接口（Gold 级扩展点）

## 调用示例
```bash
python classifier.py output/messages.jsonl output/classified.jsonl
```

## 已验证指标
金标准测试集上总体准确率 96.15%，submission / question 召回率 100%。
