"""
命令处理器模块
负责处理 Telegram 机器人的各种命令
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from .services import get_guangzhou_weather

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理 /start 命令
    发送欢迎消息并显示用户的 chat_id
    """
    chat_id = update.effective_chat.id

    message = (
        f"您好！欢迎使用您的私人助理。\n\n"
        f"您的 Chat ID 是: `{chat_id}`\n\n"
        f"请将此 ID 填入您的 `.env` 文件中的 `ADMIN_CHAT_ID` 变量，"
        f"然后重启机器人，即可启用定时问候功能。\n\n"
        f"使用 /weather 获取当前天气。\n"
        f"使用 /help 查看帮助。"
    )

    await update.message.reply_text(message, parse_mode="Markdown")
    logger.info(f"用户 {chat_id} 执行了 /start 命令")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理 /help 命令
    显示可用命令列表
    """
    message = (
        "可用命令：\n"
        "/start - 启动机器人并获取您的 Chat ID\n"
        "/weather - 立即获取广州的当前天气"
    )

    await update.message.reply_text(message)
    logger.info(f"用户 {update.effective_chat.id} 执行了 /help 命令")


async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理 /weather 命令
    获取并发送广州的当前天气信息
    """
    chat_id = update.effective_chat.id
    logger.info(f"用户 {chat_id} 请求天气信息")

    # 发送"正在获取"的提示
    processing_message = await update.message.reply_text("正在获取广州天气信息...")

    # 调用天气服务
    weather_info = await get_guangzhou_weather()

    if weather_info:
        # 成功获取天气信息
        await processing_message.edit_text(weather_info)
        logger.info(f"成功向用户 {chat_id} 发送天气信息")
    else:
        # 获取失败
        await processing_message.edit_text("抱歉，获取广州天气失败，请稍后再试。")
        logger.warning(f"向用户 {chat_id} 发送天气信息失败")
