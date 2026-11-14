# Skill: wechat-bridge（数据桥接）

## 触发词
微信群、群消息、消息提取、chatlog、消息流、数据桥接、wechat bridge

## 用途
把微信群消息流变成 Agent 可消费的标准 JSONL（Layer 1）。

## 输入 / 输出
- 输入：`--group`（群名）、`--days`（天数）、`--source`（mock / file / chatlog）
- 输出：`output/messages.jsonl`，符合 `schemas/message.schema.json`

## 依赖
- Python 3.9+，零第三方依赖
- 真实数据需本机安装 [sjzar/chatlog](https://github.com/sjzar/chatlog) 并启动其 HTTP API

## 调用示例
```bash
python wechat_bridge.py --group Elite20 --days 7 --output output/messages.jsonl
```

## 边界
只读消息，不写入微信群。
