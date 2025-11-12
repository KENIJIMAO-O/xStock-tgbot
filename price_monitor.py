"""
TSLAX 现货与合约价差监控
当价差超过阈值时，自动推送到 Telegram
"""

import time
import json
import threading
import os
from datetime import datetime
from websocket import create_connection
from dotenv import load_dotenv
import requests

# 加载环境变量
load_dotenv()

# ==================== 配置 ====================
# 从 .env 文件读取配置
SYMBOL = os.environ.get("MONITOR_SYMBOL", "TSLAX_USDT")
PRICE_DIFF_THRESHOLD = float(os.environ.get("PRICE_DIFF_THRESHOLD", "0.5"))
USE_PERCENTAGE = os.environ.get("USE_PERCENTAGE", "True").lower() == "true"
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "1"))
COOLDOWN_SECONDS = int(os.environ.get("COOLDOWN_SECONDS", "300"))

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")

# ==================== 全局变量 ====================
spot_price = None  # 现货价格
future_price = None  # 合约价格
spot_data = {}  # 现货完整数据
future_data = {}  # 合约完整数据
last_alert_time = 0  # 上次告警时间
lock = threading.Lock()  # 线程锁


# ==================== Telegram 推送函数 ====================
def send_telegram_message(message):
    """发送 Telegram 消息"""
    if not BOT_TOKEN or not ADMIN_CHAT_ID:
        print("⚠️  未配置 BOT_TOKEN 或 ADMIN_CHAT_ID，无法发送通知")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    # 检查是否需要使用代理
    proxies = None
    http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    if http_proxy:
        proxies = {
            "http": http_proxy,
            "https": http_proxy
        }

    try:
        response = requests.post(
            url,
            json={
                "chat_id": ADMIN_CHAT_ID,
                "text": message,
                "parse_mode": "HTML"
            },
            proxies=proxies,
            timeout=10
        )

        if response.status_code == 200:
            print("✅ Telegram 消息发送成功")
            return True
        else:
            print(f"❌ Telegram 消息发送失败: {response.status_code}")
            print(f"   响应内容: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Telegram 消息发送异常: {e}")
        return False


# ==================== 现货监听线程 ====================
def spot_listener():
    """监听现货价格"""
    global spot_price, spot_data

    print(f"🟢 启动现货监听: {SYMBOL}")

    while True:
        try:
            ws = create_connection("wss://api.gateio.ws/ws/v4/")
            ws.send(json.dumps({
                "time": int(time.time()),
                "channel": "spot.tickers",
                "event": "subscribe",
                "payload": [SYMBOL]
            }))

            while True:
                result = ws.recv()
                data = json.loads(result)

                if data.get("event") == "update" and data.get("channel") == "spot.tickers":
                    ticker = data["result"]

                    with lock:
                        spot_price = float(ticker["last"])
                        spot_data = {
                            "price": ticker["last"],
                            "change_24h": ticker.get("change_percentage", "N/A"),
                            "high_24h": ticker.get("high_24h", "N/A"),
                            "low_24h": ticker.get("low_24h", "N/A"),
                            "volume_24h": ticker.get("quote_volume", "N/A"),
                        }

                    print(f"📊 现货价格: {spot_price}")

        except Exception as e:
            print(f"❌ 现货连接错误: {e}，5秒后重连...")
            time.sleep(5)


# ==================== 合约监听线程 ====================
def future_listener():
    """监听合约价格"""
    global future_price, future_data

    print(f"🔵 启动合约监听: {SYMBOL}")

    while True:
        try:
            ws = create_connection("wss://fx-ws.gateio.ws/v4/ws/usdt")
            ws.send(json.dumps({
                "time": int(time.time()),
                "channel": "futures.tickers",
                "event": "subscribe",
                "payload": [SYMBOL]
            }))

            while True:
                result = ws.recv()
                data = json.loads(result)

                if data.get("event") == "update" and data.get("channel") == "futures.tickers":
                    tickers = data["result"]

                    for ticker in tickers:
                        if ticker["contract"] == SYMBOL:
                            with lock:
                                future_price = float(ticker["last"])
                                future_data = {
                                    "price": ticker["last"],
                                    "mark_price": ticker.get("mark_price", "N/A"),
                                    "index_price": ticker.get("index_price", "N/A"),
                                    "funding_rate": ticker.get("funding_rate", "N/A"),
                                    "change_24h": ticker.get("change_percentage", "N/A"),
                                    "high_24h": ticker.get("high_24h", "N/A"),
                                    "low_24h": ticker.get("low_24h", "N/A"),
                                    "volume_24h": ticker.get("volume_24h", "N/A"),
                                }

                            print(f"📊 合约价格: {future_price}")

        except Exception as e:
            print(f"❌ 合约连接错误: {e}，5秒后重连...")
            time.sleep(5)


# ==================== 价差监控线程 ====================
def price_monitor():
    """监控价差并发送告警"""
    global last_alert_time

    print(f"⚡ 启动价差监控")
    print(f"   阈值: {PRICE_DIFF_THRESHOLD}{'%' if USE_PERCENTAGE else ''}")
    print(f"   冷却时间: {COOLDOWN_SECONDS}秒\n")

    while True:
        time.sleep(CHECK_INTERVAL)

        with lock:
            if spot_price is None or future_price is None:
                continue

            # 计算价差
            price_diff = future_price - spot_price

            if USE_PERCENTAGE:
                # 使用百分比
                price_diff_pct = (price_diff / spot_price) * 100
                threshold_value = PRICE_DIFF_THRESHOLD
                current_value = abs(price_diff_pct)
                diff_display = f"{price_diff_pct:+.2f}%"
            else:
                # 使用绝对值
                threshold_value = PRICE_DIFF_THRESHOLD
                current_value = abs(price_diff)
                diff_display = f"{price_diff:+.4f}"

            # 显示当前价差
            print(f"💹 价差: {diff_display} (现货: {spot_price}, 合约: {future_price})")

            # 检查是否超过阈值
            if current_value >= threshold_value:
                current_time = time.time()

                # 检查冷却时间
                if current_time - last_alert_time >= COOLDOWN_SECONDS:
                    # 构建告警消息（使用 HTML 格式）
                    premium_line = f"<b>溢价率:</b> {price_diff_pct:.2f}%\n" if not USE_PERCENTAGE else ""

                    message = f"""🚨 <b>价差告警</b>

<b>币对:</b> {SYMBOL}
<b>价差:</b> {diff_display}
{premium_line}
📊 <b>现货信息</b>
• 价格: ${spot_data.get('price', 'N/A')}
• 24h涨跌: {spot_data.get('change_24h', 'N/A')}%
• 24h最高: ${spot_data.get('high_24h', 'N/A')}
• 24h最低: ${spot_data.get('low_24h', 'N/A')}

📊 <b>合约信息</b>
• 价格: ${future_data.get('price', 'N/A')}
• 标记价格: ${future_data.get('mark_price', 'N/A')}
• 指数价格: ${future_data.get('index_price', 'N/A')}
• 资金费率: {future_data.get('funding_rate', 'N/A')}
• 24h涨跌: {future_data.get('change_24h', 'N/A')}%

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

                    print(f"\n{'='*50}")
                    print(f"🚨 触发告警！价差: {diff_display}")
                    print(f"{'='*50}\n")

                    # 发送 Telegram 消息
                    if send_telegram_message(message):
                        last_alert_time = current_time


# ==================== 主函数 ====================
def main():
    """主函数"""
    print("="*60)
    print("🤖 TSLAX 现货/合约价差监控系统")
    print("="*60)
    print(f"监控币对: {SYMBOL}")
    print(f"价差阈值: {PRICE_DIFF_THRESHOLD}{'%' if USE_PERCENTAGE else ''}")
    print(f"通知冷却: {COOLDOWN_SECONDS}秒")
    print("="*60 + "\n")

    # 检查配置
    if not BOT_TOKEN or not ADMIN_CHAT_ID:
        print("⚠️  警告: 未配置 Telegram，将只打印告警，不发送通知")
        print("   请在 .env 文件中配置 BOT_TOKEN 和 ADMIN_CHAT_ID\n")

    # 启动三个线程
    threads = [
        threading.Thread(target=spot_listener, daemon=True, name="Spot"),
        threading.Thread(target=future_listener, daemon=True, name="Future"),
        threading.Thread(target=price_monitor, daemon=True, name="Monitor"),
    ]

    for thread in threads:
        thread.start()

    # 保持主线程运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n⏹️  停止监控")


if __name__ == "__main__":
    main()
