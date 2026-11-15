# wechat-class-manager

> 把一个微信群变成 Agent 可调用的班级管理系统——不替换微信，而是让 Agent 能**读懂、追踪、行动**群里发生的一切。

Elite20 C8（Real-World Project Execution）早期验证物 · v0.2

## 这是什么

三层架构（对应 C8 方案）：

```
Layer 3  班级管理 Skills：submission-tracker / qa-sink / class-report
Layer 2  认知层：msg-classifier（意图分类） + challenge-linker（挑战关联）
Layer 1  数据桥接：wechat_bridge（mock / file / chatlog 三种数据源）
```

当前进度：**Level 1 ✅ Level 2 ✅ Level 3（核心 skill + 周报）✅**，Level 4（Watcher 闭环）为下一阶段。

## 快速开始（零依赖，Python 3.9+）

```bash
# 1. 一键端到端（模拟数据，恒为全量 130 条确定性语料）
python pipeline.py

# 2. 单独运行各模块
python wechat_bridge.py --group Elite20 --days 7 --output output/messages.jsonl
python classifier.py output/messages.jsonl output/classified.jsonl
python submission_detector.py output/linked.jsonl output/submissions.json
python qa_extractor.py output/linked.jsonl output/qa_pairs.json
python reporter.py output/linked.jsonl output/weekly_report.md

# 3. 测试（23 个用例，含金标准准确率 + 可复现性回归）
python -m unittest discover -s tests -v
```

产物在 `output/`：标准化消息流、富化消息流、提交矩阵、问答对、自动周报。

> `--days` 只对真实数据源（`--source file` / `--source chatlog`）生效。mock 源是一份固定种子生成的完整语料，
> 刻意不施加时间窗——否则"最后一条往前 N 天"会因时间线抖动吞掉最早几条，让同一份数据在不同日期重跑得到不同条数。

## 已验证的指标

| 指标 | 结果 | 验收线 |
|---|---|---|
| 分类器总体准确率 | **96.15%**（125/130，金标准测试集） | > 70% |
| submission 召回率 | 100%（62/62） | — |
| question 召回率 | 100%（12/12） | — |
| 提交事件检测 | 32 个（学生×挑战聚合） | ≥ 5 |
| Q&A 对提取 | 12 个（回复链 12/12） | ≥ 10 |
| 挑战关联金标准覆盖率 | 91.09% | — |
| 单元测试 | 23/23 通过 | 全部通过 |

> 诚实声明：测试夹具与分类器由同一作者在同一课程语境下构造，96% 的数字存在同源偏差；
> 真实验证需接入真实群数据后重新标注测试集。这正是入选后第一周的核心任务（见 proposal R̂）。

## 目录结构

```
wechat-class-manager/
├── wechat_bridge.py        Layer 1 数据桥接 CLI
├── classifier.py           Layer 2 消息分类器（规则引擎 + LLM 扩展点）
├── challenge_linker.py     Layer 2 挑战关联器
├── submission_detector.py  Layer 3 提交追踪 + 告警
├── qa_extractor.py         Layer 3 Q&A 提取
├── reporter.py             Layer 3 周报引擎
├── pipeline.py             端到端流水线
├── make_sample_data.py     确定性模拟数据生成器（含金标准）
├── common.py               共享工具
├── schemas/                JSON Schema（message / submission / qa_pair）
├── config/                 challenges.json / group_config.json
├── skills/                 Agent Skill 封装（SKILL.md × 4）
├── tests/                  单元测试 + 金标准夹具
├── data/                   模拟示例输出
└── output/                 运行产物
```

## 接入真实数据

见 [SETUP.md](SETUP.md)——切换 `--source chatlog`，下游模块零改动（分层架构的意义）。

## 拿来主义来源

- 消息 schema 与分类标签体系：C8 WeChat Class Management Challenge 方案（课程材料）
- 数据源方案：[sjzar/chatlog](https://github.com/sjzar/chatlog)（HTTP API）、[freestylefly/wechat-cli](https://github.com/freestylefly/wechat-cli)
- Skill 封装格式：Agent SKILL.md 惯例（触发词/IO/依赖）

完整取舍分析见 `submission/王艺燃_C8_拿来说明.md`。
