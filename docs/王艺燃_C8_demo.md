# 王艺燃_C8_demo.md
## 早期验证物说明：wechat-class-manager

> 类型：**可运行原型**（Demo + 完整文档 + 测试）
> 位置：`../wechat-class-manager/`（本说明文件所在 submission 目录的旁边）
> 版本：v0.2 · 2026-11-05
> 环境：Python 3.9+，**零第三方依赖**，clone 即用
> 仓库：https://github.com/415wang417-hao/wechat-class-manager

---

## 一、它是什么

把 Elite20 班级微信群变成 Agent 可调用管理系统的原型，按 C8 方案的三层架构实现：

| 层 | 模块 | 文件 | 状态 |
|---|---|---|---|
| Layer 1 数据桥接 | 消息流提取 CLI | `wechat_bridge.py` | ✅ mock/file/chatlog 三源 |
| Layer 2 认知 | 消息意图分类器 | `classifier.py` | ✅ 规则引擎 + LLM 扩展点 |
| Layer 2 认知 | 挑战关联器 | `challenge_linker.py` | ✅ |
| Layer 3 管理Skill | 提交追踪 + 告警 | `submission_detector.py` | ✅ |
| Layer 3 管理Skill | Q&A 沉淀 | `qa_extractor.py` | ✅ |
| Layer 3 管理Skill | 周报引擎 | `reporter.py` | ✅ |
| — | 端到端流水线 | `pipeline.py` | ✅ 一条命令出全部产物 |
| — | 确定性数据生成器 | `make_sample_data.py` | ✅ 含金标准标注 |
| — | Schema / Skill 封装 | `schemas/` `skills/` | ✅ 3 schema + 4 SKILL.md |
| — | 测试 | `tests/` | ✅ 20 用例全过 |

Level 4（Watcher 闭环）未开始——这是入选后的 W7–W8 任务，不抢跑。

## 二、30 秒验证（任何人可复现）

```bash
cd wechat-class-manager
python pipeline.py                       # 端到端：130 条消息 → 5 件产物
python -m unittest discover -s tests -v  # 23 个测试全绿
```

关键验证点（对应 C8 各 Level 验收标准）：

| C8 验收标准 | 实测 | 在哪看 |
|---|---|---|
| 提取 ≥100 条群消息 | 130 条 | `output/messages.jsonl` |
| 输出符合标准 schema | ✅ 逐字段 | `schemas/message.schema.json` |
| 区分消息类型 | text/file/link/system | `output/messages.jsonl` |
| CLI 可重复运行 + 时间范围参数 | `--days`（对真实数据源生效；mock 恒为全量） | 任意重跑，两次结果逐字段一致 |
| 分类准确率 >70% | **96.15%** | `tests/test_classifier.py` 输出 |
| 检测 ≥5 个提交事件 | **32 个** | `output/submissions.json` |
| 提取 ≥10 个 QA 对 | **12 个** | `output/qa_pairs.json` |
| 模块可独立运行也可 pipeline | ✅ | README 快速开始 |
| Skill 可被 Agent 识别调用 | 4×SKILL.md 齐备 | `skills/*/SKILL.md` |

## 三、值得看的三处设计

1. **分层解耦的数据源策略**：`--source mock|file|chatlog` 切换真实/仿真数据，下游模块零改动——申请阶段无数据授权时用仿真验证架构，拿到授权后只改一个适配函数。
2. **提交完整性聚合**（v0.2 修复）：按学生×挑战聚合多条提交消息再判缺 AI 日志，避免"先交正文后补日志"被误报——来自真实测试暴露的 bug，修复过程在 AI 日志 v0.1→v0.2。
3. **确定性模拟数据 + 金标准**：`make_sample_data.py` 固定随机种子，任何人重跑得到同一份数据与同一份测试结论，测试可复核。

## 四、诚实的边界

- 96.15% 准确率测于**同源仿真数据**（夹具与分类器同一作者），真实群数据上预计回落到 70–85%，W3–W4 用 200 条真实标注重测——这是 R̂ 里写明的任务，不是隐藏风险。
- chatlog 端点对接是"最小实现"，真实接入需按其版本微调（SETUP.md 已注明）。
- 目前只有读（消息提取），没有写（回群/催交）——按方案属 Level 4 高阶选做。
