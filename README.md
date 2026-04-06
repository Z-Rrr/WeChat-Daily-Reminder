# 学习agent的代码项目

本项目实现了一个本地运行的微信定时发送应用：在电脑运行期间，按每天固定时间向指定微信会话发送自定义消息。

## 当前实现

本项目使用 Windows 桌面微信自动化（wxauto）完成发送。它不依赖个人微信开放 API，适合本地电脑常驻运行的场景。

## 环境要求

- Windows 系统
- 已安装并登录 PC 微信
- Python 3.12（推荐）

## 安装

    uv venv --python 3.12 .venv312
    .\.venv312\Scripts\python.exe -m pip install -r requirements.txt

## 配置

1. 复制示例配置：

    copy config.example.json config.json

2. 编辑 config.json。

支持两种消息来源：

- 直接填写 message 字符串
- 使用 message_source 从外部接口拉取消息，支持失败时回退到 fallback

当前示例已接入两类真实外部文案源：

- 天气：wttr.in 文本接口
- 金句：hitokoto 一言文本接口

字段说明：

- name: 任务唯一名称
- time: 24 小时制时间，格式 HH:MM
- to: 微信会话名称（联系人备注名/群名）
- message: 直接发送的内容；也支持 ${date}、${time}、${datetime}、${weekday} 变量
- message_source: 外部消息源对象，当前支持 http_json
- message_source.url: 接口地址
- message_source.json_path: 从 JSON 中提取文案的路径，例如 data.message（文本接口可不填）
- message_source.fallback: 接口失败时使用的兜底文案
- enabled: 是否启用
- timezone: 调度时区，默认 Asia/Shanghai，可改为任意 IANA 时区名（如 America/New_York）

## 运行

启动定时任务（手动打开运行即可）：

    .\.venv312\Scripts\python.exe main.py -c config.json

只预览某个任务的文案（不发微信）：

    .\.venv312\Scripts\python.exe main.py -c config.json --preview morning-weather

立刻触发某个任务并发送一次：

    .\.venv312\Scripts\python.exe main.py -c config.json --once morning-weather

运行后程序会常驻并按计划发送，按 Ctrl + C 可停止。

## 如何用电脑微信测试是否成功

建议按以下顺序测试：

1. 文案测试（不触发微信）

- 先运行 preview 命令，确认能返回天气或金句文本。
- 如果返回 fallback 文案，说明接口不可达，但程序降级正常。

1. 微信链路测试（立即触发）

- 打开并登录 PC 微信。
- 在 config.json 中把 to 设为 文件传输助手。
- 运行 once 命令，观察微信是否自动切换到对应会话并发送消息。

1. 定时测试（验证调度）

- 把某个任务时间改成当前时间后 1 到 2 分钟。
- 运行 .\.venv312\Scripts\python.exe main.py -c config.json 挂着不关。
- 到时间后观察微信是否自动发送。

1. 结果确认

- 微信聊天窗口能看到消息，视为发送成功。
- logs/app.log 中出现 job_start 和 job_success 记录，视为调度与发送都成功。

## 日志

运行日志会写入 logs/app.log，包含任务开始、成功、失败等信息。

## 注意事项

- 仅在电脑开机且程序运行期间生效。
- 依赖桌面微信 UI 自动化，发送时可能会短暂切到微信窗口。
- 首次使用请先把发送对象名称填写为 文件传输助手 做测试。
- 外部接口建议准备兜底文案，避免接口异常导致空消息。
