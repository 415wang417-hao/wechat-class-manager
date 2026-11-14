# SETUP.md — 安装与配置

## 环境要求

- Python **3.9+**（开发环境 3.13.14）
- **零第三方依赖**：全部标准库实现，clone 即用

## 5 分钟跑通（模拟数据）

```bash
python make_sample_data.py   # 重新生成确定性模拟数据（可选）
python pipeline.py           # 端到端流水线
python -m unittest discover -s tests -v   # 23 个测试
```

## 接入真实微信群数据

### 方式一：chatlog（推荐，Windows 可用）

1. 安装 [sjzar/chatlog](https://github.com/sjzar/chatlog)：`go install github.com/sjzar/chatlog@latest` 或下载 release
2. 首次运行 `chatlog` 完成本地微信数据库解密（详见其 README）
3. 启动 HTTP API：`chatlog server --port 5030`
4. 切换数据源：

```bash
python pipeline.py --source chatlog   # 需先在 wechat_bridge.fetch_from_chatlog 中确认端点
```

> 当前 `fetch_from_chatlog()` 已实现最小对接（`/api/v1/chatlog?talker=<群名>&days=<N>`）。
> chatlog 版本迭代可能调整端点，接入时对照其 API 文档微调——桥接层只有这一个函数需要改，
> 这是分层设计的直接收益。

### 方式二：文件导入

任何工具导出的 JSONL（含 msg_id / timestamp / sender / type / content 字段）都能直接用：

```bash
python pipeline.py --source file --input your_export.jsonl --days 10
```

### 数据脱敏提醒

真实群数据包含他人隐私。接入前：
1. 只处理与课程管理相关的字段
2. nickname / wechat_id 做映射表脱敏
3. 导出示例输出前移除 media_ref 中的本地路径

## 配置文件

- `config/challenges.json`：挑战编号、截止日期、必备文件——课程更新时改这里
- `config/group_config.json`：群成员、老师列表——角色判定（announcement 分类）依赖此文件

## 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| `--days 7` 取不到数据 | 模拟数据时间窗以最后一条消息为基准 | 用 `--days 10` 或调大 |
| chatlog 连接失败 | API 未启动 / 端口不符 | 确认 `chatlog server` 状态，检查 `fetch_from_chatlog` 中 base_url |
| Windows 控制台中文乱码 | 编码问题 | `chcp 65001` 或用 Windows Terminal |
