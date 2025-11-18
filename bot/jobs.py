"""
定时任务模块
负责处理机器人的定时任务，如每日早安问候
"""

import os
import logging
from telegram.ext import ContextTypes
from .services import get_guangzhou_weather

logger = logging.getLogger(__name__)


async def send_morning_greeting(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    发送早安问候消息
    每天早上 8:00 自动执行，向管理员发送早安问候和天气信息
    """
    # 从环境变量获取管理员 Chat ID
    admin_chat_id = os.environ.get("ADMIN_CHAT_ID")

    # 检查 ADMIN_CHAT_ID 是否已设置
    if not admin_chat_id or admin_chat_id.strip() == "":
        logger.warning("ADMIN_CHAT_ID 未设置，无法发送晨间问候")
        return

    logger.info(f"开始发送晨间问候给 Chat ID: {admin_chat_id}")

    # 获取天气信息
    weather_info = await get_guangzhou_weather()

    # 构建问候消息
    if weather_info:
        # 天气获取成功
        message = f"早上好！{weather_info}。祝您有美好的一天！"
        logger.info("成功获取天气信息，准备发送晨间问候")
    else:
        # 天气获取失败，使用备用文案
        message = "早上好！今天获取天气失败了，但依然祝您有美好的一天！"
        logger.warning("获取天气信息失败，使用备用问候消息")

    # 发送消息
    try:
        await context.bot.send_message(
            chat_id=admin_chat_id,
            text=message
        )
        logger.info(f"成功发送晨间问候给 Chat ID: {admin_chat_id}")
    except Exception as e:
        logger.error(f"发送晨间问候失败: {e}")
