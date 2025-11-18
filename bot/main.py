"""
Telegram 机器人主程序
个人助理机器人 - 提供天气查询和每日早安问候功能
"""

import os
import logging
import datetime
import pytz
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler

# 导入自定义模块
from .handlers import start_command, help_command, weather_command
from .jobs import send_morning_greeting

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main() -> None:
    """
    主函数：初始化机器人、注册命令处理器和定时任务
    """
    # 加载环境变量
    load_dotenv()

    # 获取机器人令牌
    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        logger.error("错误: BOT_TOKEN 未在 .env 文件中设置")
        return

    logger.info("正在启动 Telegram 机器人...")

    # 创建 Application 实例
    application = Application.builder().token(bot_token).build()

    # 注册命令处理器
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("weather", weather_command))
    logger.info("命令处理器注册完成")

    # 获取 JobQueue
    job_queue = application.job_queue

    # 设置定时任务：每天早上 8:00 (北京时间) 发送问候
    if job_queue:
        # 指定时区为亚洲/上海 (中国标准时间)
        shanghai_tz = pytz.timezone('Asia/Shanghai')

        # 设置每日定时任务
        job_queue.run_daily(
            callback=send_morning_greeting,
            time=datetime.time(hour=8, minute=0, second=0, tzinfo=shanghai_tz),
            name="daily_morning_greeting"
        )
        logger.info("定时任务已设置：每天早上 8:00 (北京时间) 发送问候")

        # 检查 ADMIN_CHAT_ID 是否已配置
        admin_chat_id = os.environ.get("ADMIN_CHAT_ID")
        if not admin_chat_id or admin_chat_id.strip() == "":
            logger.warning(
                "注意: ADMIN_CHAT_ID 未设置。"
                "请使用 /start 命令获取您的 Chat ID，"
                "并将其添加到 .env 文件中，然后重启机器人。"
            )
        else:
            logger.info(f"ADMIN_CHAT_ID 已配置: {admin_chat_id}")
    else:
        logger.error("错误: 无法获取 JobQueue")

    # 启动机器人
    logger.info("机器人启动成功，正在运行...")
    application.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
