📋 Telegram 机器人项目技术实现需求文档 (V2)
致AI（Claude Code）： 请严格按照以下技术需求文档，为我生成一个完整的、可运行的 Telegram 机器人项目。项目需包含所有指定的功能、文件结构和依赖项。

1. 项目概述

项目名称： 个人助理机器人

项目目标： 创建一个 Telegram 机器人，该机器人能与特定用户（我）交互，核心功能包括：

按命令即时推送广州的天气。

每天早上 8:00 定时向我发送早安问候，并附带当日的广州天气预报。

2. 技术栈 (Tech Stack)

编程语言： Python 3.10 或更高版本。

核心框架： python-telegram-bot (必须使用 v20.0 或更高的异步版本，基于 asyncio)。

定时任务： 使用 python-telegram-bot 内置的 JobQueue (作业队列) 功能。

HTTP 请求： httpx (用于异步 API 请求)。

依赖管理： 提供一个 requirements.txt 文件。

配置管理： 机器人令牌和 API 密钥必须通过 .env 文件加载，使用 python-dotenv 库。

3. 环境变量

请在 .env 文件中配置以下变量：

BOT_TOKEN: 您的 Telegram 机器人令牌。

WEATHER_API_KEY: 用于天气 API 的密钥。

ADMIN_CHAT_ID: (关键) 接收晨间问候的用户的 Telegram Chat ID。

注：请在代码中提供获取 ADMIN_CHAT_ID 的简单方法（例如，通过 /start 命令让用户自己获取）。

4. 核心功能需求 (Handlers & Jobs)

4.1. 基础命令

/start

触发： 用户发送 /start 命令。

响应： 1. 发送欢迎消息。 2. (关键) 回复用户其专属的 chat_id，以便用户将其配置到 .env 文件的 ADMIN_CHAT_ID 中。

消息内容： 您好！欢迎使用您的私人助理。 \n\n您的 Chat ID 是: \{chat_id}` \n\n请将此 ID 填入您的 `.env` 文件中的 `ADMIN_CHAT_ID` 变量，然后重启机器人，即可启用定时问候功能。 \n\n使用 /weather 获取当前天气。 \n使用 /help 查看帮助。(请注意使用 Markdown 的 来格式化chat_id` 以便复制)。

/help

触发： 用户发送 /help 命令。

响应： 可用命令：\n/start - 启动机器人并获取您的 Chat ID\n/weather - 立即获取广州的当前天气

4.2. 天气功能 (API 调用)

服务模块 (services.py)：

创建一个异步函数 get_guangzhou_weather()。

API 选择： 使用 OpenWeatherMap (OWM) 的免费 "Current Weather Data" API。

API 端点： https://api.openweathermap.org/data/2.5/weather

参数： q=Guangzhou, appid={WEATHER_API_KEY}, units=metric (使用摄氏度), lang=zh_cn (中文)。

逻辑：

使用 httpx.AsyncClient 发起 GET 请求。

处理响应 (JSON)。

提取天气描述 ( weather[0].description ) 和温度 ( main.temp )。

返回： 返回一个格式化字符串，例如："广州当前天气：晴，气温：25.3°C"。

错误处理： 如果 API 请求失败或返回非 200 状态码，应返回 None 或抛出异常，由调用方处理。

命令处理器 (handlers.py)：

触发命令： /weather

功能描述： 用户发送 /weather 时，调用 services.get_guangzhou_weather() 函数。

响应：

成功：回复 get_guangzhou_weather() 返回的天气字符串。

失败：回复 "抱歉，获取广州天气失败，请稍后再试。"

4.3. 定时任务 (Job Queue)

作业回调函数 (jobs.py)：

创建一个异步回调函数 send_morning_greeting(context: ContextTypes.DEFAULT_TYPE)。

逻辑：

从环境变量 os.environ.get("ADMIN_CHAT_ID") 中获取 ADMIN_CHAT_ID。

(重要) 检查 ADMIN_CHAT_ID 是否已设置。如果未设置或为空，则在日志中打印一条警告（例如 "ADMIN_CHAT_ID 未设置，无法发送晨间问候"）并直接 return。

调用 services.get_guangzhou_weather() 获取天气信息。

构建问候消息。如果天气获取失败，则使用备用文案。

使用 context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=message_content) 发送消息。

消息内容 (成功)： "早上好！[这里插入天气信息，例如：广州当前天气：晴，25.3°C]。祝您有美好的一天！"

消息内容 (天气失败)： "早上好！今天获取天气失败了，但依然祝您有美好的一天！"

主程序设置 (main.py)：

在 main.py 中初始化 Application 后，必须获取 job_queue。

定时设置：

使用 job_queue.run_daily()。

时间： datetime.time(hour=8, minute=0, second=0)。

时区： 必须指定时区。使用 pytz.timezone('Asia/Shanghai')。 (因此 pytz 也是一个依赖)。

回调： jobs.send_morning_greeting。

名称： "daily_morning_greeting"。

5. 代码结构 (必须遵守)

请将所有代码组织在以下结构中：

telegram_bot/
├── main.py         # 主程序入口：加载env, 设置App, 注册Job, 注册Handler
├── handlers.py     # 存放命令处理器：start, help, weather_command
├── services.py     # 存放API调用逻辑：get_guangzhou_weather
├── jobs.py         # 存放Job回调函数：send_morning_greeting
├── requirements.txt  # 依赖列表
├── .env.example    # 环境变量示例文件
└── .gitignore
6. 预期交付物

main.py 的完整代码。

handlers.py 的完整代码。

services.py 的完整代码。

jobs.py 的完整代码。

requirements.txt 文件的内容 (应包含 python-telegram-bot[job-queue], python-dotenv, httpx, pytz)。

.env.example 文件的内容 (包含 BOT_TOKEN=, WEATHER_API_KEY=, ADMIN_CHAT_ID=)。

简短的“如何运行”说明（安装依赖、创建 .env、运行 /start 获取ID、配置ID、启动 main.py）。