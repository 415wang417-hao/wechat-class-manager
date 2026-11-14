# -*- coding: utf-8 -*-
"""确定性模拟数据生成器：仿真 Elite20 班级微信群 10 天消息流。

为什么需要它：
  Level 1 要求从真实微信数据库提取消息；在申请阶段（无真实群数据授权时），
  用可复现的模拟数据驱动全流水线，验证架构与算法。真实部署时只需把
  --source 切换为 chatlog / file（见 SETUP.md），下游模块零改动——这正是
  分层架构的意义。

同时输出两份产物：
  tests/fixtures/sample_messages.jsonl —— 带金标准（label / gold_refs），用于分类准确率测试
  data/sample_output.jsonl —— 干净版本（含 label 字段会被剥离），作为桥接示例输出
"""
import json
import os
import random

random.seed(20261105)

STUDENTS = [
    "王艺燃", "陈默", "李华", "赵欣", "孙磊", "周雨", "吴强", "郑楠", "林晓", "何佳",
    "陆遥", "高飞", "徐婷", "马亮", "曹悦", "韩鑫", "邓科", "冯琳", "肖宇", "叶琪",
]
TEACHER = ("teacher_neolaf", "王老师")
BASE = "2026-10-26T08:00:00"


def _wid(name):
    pinyin = {"王艺燃": "wx_wangyiran", "陈默": "wx_chenmo", "李华": "wx_lhua", "赵欣": "wx_zhaoxin",
              "孙磊": "wx_sunlei", "周雨": "wx_zhouyu", "吴强": "wx_wuqiang", "郑楠": "wx_zhengnan",
              "林晓": "wx_linxiao", "何佳": "wx_hejia", "陆遥": "wx_luyao", "高飞": "wx_gaofei",
              "徐婷": "wx_xuting", "马亮": "wx_maliang", "曹悦": "wx_caoyue", "韩鑫": "wx_hanxin",
              "邓科": "wx_dengke", "冯琳": "wx_fenglin", "肖宇": "wx_xiaoyu", "叶琪": "wx_yeqi"}
    return pinyin.get(name, "wx_" + name)


class Timeline:
    """递增时间戳的确定性时间线。"""

    def __init__(self, base=BASE):
        from datetime import datetime, timedelta

        self.t = datetime.fromisoformat(base)
        self.step = timedelta(hours=1.6)

    def next(self, jitter=True):
        if jitter:
            self.t += self.step * random.uniform(0.1, 2.3)
        else:
            self.t += self.step
        return self.t.isoformat()


def build():
    # 每次生成都重置种子：模块顶层那次 seed 只对"导入后的第一次生成"有效，
    # 同一进程内第二次调用会顺着已消耗的随机序列继续走，得到另一份语料。
    # 这会让 fetch_from_mock 两次调用的结果不同（条数相同、时间戳全变），
    # 也会让"确定性可复现"的对外承诺只在单次进程内成立。故在此显式重置。
    random.seed(20261105)
    tl = Timeline()
    msgs = []

    def add(sender, mtype, content, label, gold_refs=None, media=None, reply_to=None):
        ts = tl.next()
        msg = {
            "msg_id": f"m{len(msgs) + 1:04d}",
            "timestamp": ts,
            "sender": {"wechat_id": _wid(sender) if sender != "王老师" else TEACHER[0],
                       "nickname": sender},
            "type": mtype,
            "content": content,
            "media_ref": media,
            "reply_to": reply_to,
            "_label": label,
            "_gold_refs": gold_refs or [],
        }
        msgs.append(msg)
        return msg["msg_id"]

    # ===== Day 1：老师开营通知 =====
    add("王老师", "text",
        "@全体 各位同学，C5 GitHub Repository 已正式发布，截止 11月9日 23:59，提交前请对照检查清单自查。",
        "announcement", ["C5"])
    add("王老师", "text",
        "提醒：所有挑战提交都必须包含 AI 日志，缺少 AI 日志的提交会被退回补交。",
        "announcement", None)
    add("李华", "text", "收到，老师！", "social")
    add("陈默", "text", "早呀各位", "social")
    add("孙磊", "text",
        "分享一个 GitHub Actions 的中文教程，写得挺清楚的，做 C5 的同学可以看看 https://example.com/actions-tutorial",
        "resource", ["C5"])
    add("周雨", "text", "谢谢分享", "social")

    # ===== Day 1-2：C4 收尾提交 =====
    for name in ["王艺燃", "陈默", "李华", "赵欣", "周雨", "吴强", "郑楠", "林晓"]:
        add(name, "file", "C4 提交", "submission", ["C4"],
            media=f"attachments/{name}_C4_技能分享.md")
        add(name, "file", "AI日志一并提交", "submission", ["C4"],
            media=f"attachments/{name}_C4_AI日志.md")

    # ===== Day 2：问答（回复链）=====
    q1 = add("何佳", "text", "请问 C4 的技能分享一定要用 SKILL.md 格式吗？还是 Markdown 就行？", "question", ["C4"])
    add("王艺燃", "text",
        "要按标准 SKILL.md 格式来写，我看了课程文档，里面有触发词、输入输出和依赖三个必填部分，你对照着填就行。",
        "answer", ["C4"], reply_to=q1)
    add("何佳", "text", "明白了，谢谢！", "social")

    q2 = add("陆遥", "text", "git push 的时候报错 non-fast-forward 怎么办？我卡了半小时了", "question", ["C5"])
    add("高飞", "text",
        "先 git pull --rebase origin main 再 push。报错的原因是你本地分支落后于远端，rebase 把你的提交挪到远端最新提交之后就可以了。",
        "answer", ["C5"], reply_to=q2)
    add("陆遥", "text", "搞定了，感谢！", "social")

    q3 = add("徐婷", "text", "有没有人知道公众号文章的封面图尺寸是多少？", "question", ["C7"])
    add("马亮", "text",
        "头图 900×383，次条 200×200。我上周刚做完 C7 的文章，这些尺寸是官方要求的。",
        "answer", ["C7"], reply_to=q3)
    add("徐婷", "text", "太好了谢谢", "social")

    # ===== Day 3：闲聊 + 讨论 =====
    add("曹悦", "text", "今天食堂居然有糖醋排骨 哈哈", "social")
    add("韩鑫", "text", "羡慕，我们这边只有大锅菜", "social")
    add("邓科", "text",
        "说正事：C6 我打算用纯前端方案部署，不用后端，这样静态托管就能上线，成本最低。",
        "discussion", ["C6"])
    add("冯琳", "text",
        "C6 我也是这个思路，不过数据得存 localStorage，刷新不丢就行。等 C6 正式开始我们组个队？",
        "discussion", ["C6"])
    add("邓科", "text", "可以，到时候拉个小群", "social")
    add("王老师", "link",
        "本周三晚 8 点班级周会，议题是 C5 提交检查清单和中途答疑，请准时参加 https://meeting.example.com/elite20",
        "announcement", ["C5"])

    # ===== Day 3-4：C5 提交高峰 =====
    for name in ["王艺燃", "陈默", "李华", "赵欣", "孙磊", "周雨", "吴强", "郑楠", "林晓", "何佳", "陆遥", "高飞"]:
        add(name, "file", "C5 提交", "submission", ["C5"],
            media=f"attachments/{name}_C5_repo链接.md")
        add(name, "file", "AI日志", "submission", ["C5"],
            media=f"attachments/{name}_C5_AI日志.md")
    # 少数人交了但没有 AI 日志（完整性告警场景）
    add("徐婷", "file", "C5 提交", "submission", ["C5"], media="attachments/徐婷_C5_repo链接.md")
    add("马亮", "file", "提交 C5", "submission", ["C5"], media="attachments/马亮_C5_repo链接.md")

    # ===== Day 4：更多问答 =====
    q4 = add("肖宇", "text", "repo 要开源还是可以私有？课程有要求吗？", "question", ["C5"])
    add("叶琪", "text",
        "必须开源，而且 README 里要写清楚安装和使用说明，这是产物完整性的评分维度之一。私有仓库评审老师看不到。",
        "answer", ["C5"], reply_to=q4)
    add("肖宇", "text", "好的，我这就改 public", "social")

    q5 = add("李华", "text", "C5 的 shipcheck 体检要达到多少分才算过？", "question", ["C5"])
    add("王艺燃", "text",
        "90 分以上是 A 级达标线，我自己跑到 100 分。重点是五大维度都要过 80，单项瘸腿会拉低总分。",
        "answer", ["C5"], reply_to=q5)

    q6 = add("郑楠", "text", "有人做完 C2 的文献综述了吗？引用格式用 APA 还是 GB/T？", "question", ["C2"])
    add("林晓", "text",
        "用 APA 7th。课程模板里写的是 APA，而且 Zotero 导出直接支持 APA 格式，省得手动调。",
        "answer", ["C2"], reply_to=q6)
    add("郑楠", "text", "学到了", "social")

    # ===== Day 5：资源分享 + 讨论 =====
    add("何佳", "link", "推荐一个 Zotero + AI 插件的用法，写论文的时候自动整理文献 https://example.com/zotero-ai", "resource", ["C2"])
    add("陆遥", "text", "这个好，收藏了", "social")
    add("高飞", "text",
        "C6 的仪表盘我想直接复用 ECharts，不自己手写 SVG。上次 C6A 用过一遍，心智负担小很多。",
        "discussion", ["C6"])
    add("徐婷", "text", "ECharts 文档很全，中文的，适合我们这种场景", "discussion", ["C6"])
    add("孙磊", "text", "晚上有人一起自习吗", "social")
    add("周雨", "text", "我来，图书馆三楼见", "social")

    # ===== Day 6：C6 提交开始 =====
    for name in ["王艺燃", "陈默", "赵欣", "吴强", "林晓", "何佳", "高飞", "徐婷", "邓科", "冯琳"]:
        add(name, "file", "C6 提交", "submission", ["C6"],
            media=f"attachments/{name}_C6_部署链接.md")
        add(name, "file", "AI日志", "submission", ["C6"],
            media=f"attachments/{name}_C6_AI日志.md")

    q7 = add("马亮", "text", "部署完的 Web App 打不开怎么办？页面一直转圈", "question", ["C6"])
    add("邓科", "text",
        "先看浏览器控制台有没有报错。如果是端口问题，检查你本地的服务是否还活着；如果是路径问题，大概率是 build 之后 index.html 里的资源引用是绝对路径，改成相对路径重新 build 一次。",
        "answer", ["C6"], reply_to=q7)
    add("马亮", "text", "原来是路径问题，解决了，谢谢！", "social")

    q8 = add("曹悦", "text", "C7 的文章一定要发公众号吗？知乎行不行？", "question", ["C7"])
    add("韩鑫", "text",
        "以公众号为主，因为要拿到阅读量和在看数据做传播验证。知乎可以作为二次分发的渠道，但主链接必须交给公众号的。",
        "answer", ["C7"], reply_to=q8)
    add("曹悦", "text", "明白了", "social")

    # ===== Day 7：老师阶段总结 + 社交 =====
    add("王老师", "text",
        "@全体 C5 已收到 14 份提交，还有 6 位同学未交，截止日 11月9日，请抓紧。已交的同学注意检查 AI 日志是否齐全。",
        "announcement", ["C5"])
    add("王老师", "text",
        "本周整体活跃度不错，特别表扬王艺燃、高飞、邓科几位同学在群里的高质量回答。",
        "announcement")
    add("叶琪", "text", "被表扬了 不好意思哈哈", "social")
    add("孙磊", "text", "恭喜恭喜 🎉", "social")
    add("王艺燃", "text", "互相学习，大家都加油", "social")

    # ===== Day 8：C8 预热讨论 =====
    add("王老师", "text",
        "预告：C8 真实项目项目池下周公布，包含微信群班级管理 Agent、企业本体系统、课程生产体系三个方向，提前想好意向。",
        "announcement", ["C8"])
    add("李华", "text",
        "微信群班级管理这个方向很实用，我们的群消息每天几百条，好问题全被淹没了，做成 Agent 查询太需要了。",
        "discussion", ["C8"])
    add("陈默", "text",
        "对，提交追踪也是痛点，老师手动翻文件太费劲。我先研究下 chatlog 这个开源工具能不能提取本地微信数据。",
        "discussion", ["C8"])
    add("王艺燃", "text",
        "我可以先把消息分类器和提交检测器的原型做出来，用模拟数据跑通，等数据源接上就能直接用。",
        "discussion", ["C8"])
    add("赵欣", "text", "这个思路靠谱，期待原型", "social")

    q9 = add("肖宇", "text", "chatlog 支持Windows吗？我是 Windows 系统", "question", ["C8"])
    add("陈默", "text",
        "支持，Windows 和 macOS 都可以，解密本地数据库之后开一个 HTTP API 就能查历史消息。GitHub 上文档很全，你直接搜 sjzar/chatlog。",
        "answer", ["C8"], reply_to=q9)
    add("肖宇", "text", "太好了，感谢分享", "social")

    # ===== Day 9：零散问答与闲聊 =====
    q10 = add("周雨", "text", "proposal 里的 KSTAR 结构是什么意思？第一次见这种写法", "question", ["C8"])
    add("王艺燃", "text",
        "K 是已有知识和资源，S 是当前情境，T 是任务分解，A 是行动计划，R 是预期结果。整个挑战体系都在用这个循环，AAR 里的 R 和 R 对比就是它的学习信号。",
        "answer", ["C8"], reply_to=q10)
    add("周雨", "text", "原来如此，清楚了", "social")

    q11 = add("吴强", "text", "拿来说明是什么？和参考文献有什么区别？", "question", ["C8"])
    add("叶琪", "text",
        "区别在于取舍：参考文献只列来源，拿来说明必须写清楚哪些直接复用、哪些删掉、哪些重构，证明你不是抄而是消化过。",
        "answer", ["C8"], reply_to=q11)

    add("马亮", "text", "周末愉快各位，下周继续冲", "social")
    add("邓科", "text", "下周 C8 项目池公布，感觉要忙起来了", "social")
    add("冯琳", "text", "哈哈已经预感到了", "social")

    # ===== Day 10：收尾 =====
    add("王老师", "text",
        "@全体 提醒：C6 截止 11月16日，还有部分同学没交部署链接。另外 C8 proposal 的早期验证物占 70% 权重，别只写文档。",
        "announcement", ["C6", "C8"])
    add("林晓", "text", "收到", "social")
    q12 = add("何佳", "text", "部署链接需要附源码仓库吗？", "question", ["C6"])
    add("高飞", "text",
        "需要，部署链接给评审老师直接体验，源码仓库让他们能验证实现。两个都要放在提交文档里，缺一不可。",
        "answer", ["C6"], reply_to=q12)
    add("何佳", "text", "明白了谢谢", "social")
    add("王艺燃", "text",
        "C8 的原型我这两天推进，先把模拟数据流水线跑出来，周末发群里给大家看看。",
        "discussion", ["C8"])

    return msgs


def generate_sample_messages(group="Elite20"):
    """返回原始消息列表（含 _label 内部字段，桥接输出前会被剥离）。"""
    return build()


def export():
    here = os.path.dirname(os.path.abspath(__file__))
    msgs = build()

    # 带金标准的测试夹具
    fixture_dir = os.path.join(here, "tests", "fixtures")
    os.makedirs(fixture_dir, exist_ok=True)
    with open(os.path.join(fixture_dir, "sample_messages.jsonl"), "w", encoding="utf-8") as f:
        for m in msgs:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")

    # 干净的桥接示例输出（剥离内部字段）
    data_dir = os.path.join(here, "data")
    os.makedirs(data_dir, exist_ok=True)
    clean_keys = ("msg_id", "timestamp", "sender", "type", "content", "media_ref", "reply_to")
    with open(os.path.join(data_dir, "sample_output.jsonl"), "w", encoding="utf-8") as f:
        for m in msgs:
            f.write(json.dumps({k: m[k] for k in clean_keys}, ensure_ascii=False) + "\n")

    from collections import Counter

    dist = Counter(m["_label"] for m in msgs)
    print(f"共生成 {len(msgs)} 条消息")
    print("意图分布:", dict(dist.most_common()))
    print(f"夹具 → {os.path.join(fixture_dir, 'sample_messages.jsonl')}")
    print(f"示例输出 → {os.path.join(data_dir, 'sample_output.jsonl')}")


if __name__ == "__main__":
    export()
