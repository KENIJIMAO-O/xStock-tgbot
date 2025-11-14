"""
TSLAX 现货与合约价差监控
当价差超过阈值时，自动推送到 Telegram
"""

import time
import json
import threading
import os
from datetime import datetime
import pytz
from websocket import create_connection
from dotenv import load_dotenv
import requests

# 加载环境变量
load_dotenv()

# ==================== 配置 ====================
# 从 .env 文件读取配置
SYMBOLS_STR = os.environ.get("MONITOR_SYMBOLS", "TSLAX_USDT")
SYMBOLS = [s.strip() for s in SYMBOLS_STR.split(",")]  # 支持多个币对
PRICE_DIFF_THRESHOLD = float(os.environ.get("PRICE_DIFF_THRESHOLD", "0.5"))
USE_PERCENTAGE = os.environ.get("USE_PERCENTAGE", "True").lower() == "true"
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "1"))
COOLDOWN_SECONDS = int(os.environ.get("COOLDOWN_SECONDS", "300"))

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")

# 为每个币对加载独立阈值（如果配置了）
THRESHOLDS = {}
for symbol in SYMBOLS:
    threshold_key = f"THRESHOLD_{symbol.replace('-', '_')}"
    custom_threshold = os.environ.get(threshold_key)
    if custom_threshold:
        THRESHOLDS[symbol] = float(custom_threshold)
    else:
        THRESHOLDS[symbol] = PRICE_DIFF_THRESHOLD

# ==================== 全局变量 ====================
# 多币对数据结构：字典存储
spot_prices = {}     # {"TSLAX_USDT": 439.98, "AAPL_USDT": 180.50}
future_prices = {}   # {"TSLAX_USDT": 440.42, "AAPL_USDT": 181.00}
spot_data = {}       # {"TSLAX_USDT": {...}, "AAPL_USDT": {...}}
future_data = {}     # {"TSLAX_USDT": {...}, "AAPL_USDT": {...}}
last_alert_times = {}  # {"TSLAX_USDT": 1234567890, "AAPL_USDT": 0}

# 初始化冷却时间
for symbol in SYMBOLS:
    last_alert_times[symbol] = 0

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
    """监听现货价格 - 支持多币对"""
    global spot_prices, spot_data

    print(f"🟢 启动现货监听: {', '.join(SYMBOLS)}")

    while True:
        try:
            ws = create_connection("wss://api.gateio.ws/ws/v4/")
            ws.send(json.dumps({
                "time": int(time.time()),
                "channel": "spot.tickers",
                "event": "subscribe",
                "payload": SYMBOLS  # 一次订阅多个币对
            }))

            while True:
                result = ws.recv()
                data = json.loads(result)

                if data.get("event") == "update" and data.get("channel") == "spot.tickers":
                    ticker = data["result"]
                    symbol = ticker["currency_pair"]  # 获取币对名称

                    # 只处理我们监控的币对
                    if symbol in SYMBOLS:
                        with lock:
                            spot_prices[symbol] = float(ticker["last"])
                            spot_data[symbol] = {
                                "price": ticker["last"],
                                "change_24h": ticker.get("change_percentage", "N/A"),
                                "high_24h": ticker.get("high_24h", "N/A"),
                                "low_24h": ticker.get("low_24h", "N/A"),
                                "volume_24h": ticker.get("quote_volume", "N/A"),
                            }

                        print(f"📊 现货 {symbol}: {spot_prices[symbol]}")

        except Exception as e:
            print(f"❌ 现货连接错误: {e}，5秒后重连...")
            time.sleep(5)


# ==================== 合约监听线程 ====================
def future_listener():
    """监听合约价格 - 支持多币对"""
    global future_prices, future_data

    print(f"🔵 启动合约监听: {', '.join(SYMBOLS)}")

    while True:
        try:
            ws = create_connection("wss://fx-ws.gateio.ws/v4/ws/usdt")
            ws.send(json.dumps({
                "time": int(time.time()),
                "channel": "futures.tickers",
                "event": "subscribe",
                "payload": SYMBOLS  # 一次订阅多个币对
            }))

            while True:
                result = ws.recv()
                data = json.loads(result)

                if data.get("event") == "update" and data.get("channel") == "futures.tickers":
                    tickers = data["result"]

                    for ticker in tickers:
                        symbol = ticker["contract"]  # 获取合约名称

                        # 只处理我们监控的币对
                        if symbol in SYMBOLS:
                            with lock:
                                future_prices[symbol] = float(ticker["last"])
                                future_data[symbol] = {
                                    "price": ticker["last"],
                                    "mark_price": ticker.get("mark_price", "N/A"),
                                    "index_price": ticker.get("index_price", "N/A"),
                                    "funding_rate": ticker.get("funding_rate", "N/A"),
                                    "change_24h": ticker.get("change_percentage", "N/A"),
                                    "high_24h": ticker.get("high_24h", "N/A"),
                                    "low_24h": ticker.get("low_24h", "N/A"),
                                    "volume_24h": ticker.get("volume_24h", "N/A"),
                                }

                            print(f"📊 合约 {symbol}: {future_prices[symbol]}")

        except Exception as e:
            print(f"❌ 合约连接错误: {e}，5秒后重连...")
            time.sleep(5)


# ==================== 价差监控线程 ====================
def price_monitor():
    """监控价差并发送告警 - 支持多币对"""
    global last_alert_times

    print(f"⚡ 启动价差监控")
    print(f"   监控币对: {', '.join(SYMBOLS)}")
    for symbol in SYMBOLS:
        print(f"   {symbol} 阈值: {THRESHOLDS[symbol]}{'%' if USE_PERCENTAGE else ''}")
    print(f"   冷却时间: {COOLDOWN_SECONDS}秒\n")

    while True:
        time.sleep(CHECK_INTERVAL)

        # 遍历所有币对
        for symbol in SYMBOLS:
            with lock:
                # 检查该币对的数据是否已接收
                if symbol not in spot_prices or symbol not in future_prices:
                    continue

                spot_price = spot_prices[symbol]
                future_price = future_prices[symbol]

            # 计算价差
            price_diff = future_price - spot_price

            if USE_PERCENTAGE:
                # 使用百分比
                price_diff_pct = (price_diff / spot_price) * 100
                threshold_value = THRESHOLDS[symbol]
                current_value = abs(price_diff_pct)
                diff_display = f"{price_diff_pct:+.2f}%"
            else:
                # 使用绝对值
                threshold_value = THRESHOLDS[symbol]
                current_value = abs(price_diff)
                diff_display = f"{price_diff:+.4f}"

            # 显示当前价差
            print(f"💹 {symbol} 价差: {diff_display} (现货: {spot_price:.2f}, 合约: {future_price:.2f})")

            # 检查是否超过阈值
            if current_value >= threshold_value:
                current_time = time.time()

                # 检查该币对的冷却时间
                if current_time - last_alert_times[symbol] >= COOLDOWN_SECONDS:
                    # 构建告警消息（使用 HTML 格式）
                    with lock:
                        symbol_spot_data = spot_data.get(symbol, {})
                        symbol_future_data = future_data.get(symbol, {})

                    premium_line = f"<b>溢价率:</b> {price_diff_pct:.2f}%\n" if not USE_PERCENTAGE else ""

                    # 获取上海时区的当前时间
                    shanghai_tz = pytz.timezone('Asia/Shanghai')
                    now_shanghai = datetime.now(shanghai_tz)

                    message = f"""🚨 <b>价差告警</b>

<b>币对:</b> {symbol}
<b>价差:</b> {diff_display}
{premium_line}
📊 <b>现货信息</b>
• 价格: ${symbol_spot_data.get('price', 'N/A')}
• 24h涨跌: {symbol_spot_data.get('change_24h', 'N/A')}%
• 24h最高: ${symbol_spot_data.get('high_24h', 'N/A')}
• 24h最低: ${symbol_spot_data.get('low_24h', 'N/A')}

📊 <b>合约信息</b>
• 价格: ${symbol_future_data.get('price', 'N/A')}
• 标记价格: ${symbol_future_data.get('mark_price', 'N/A')}
• 指数价格: ${symbol_future_data.get('index_price', 'N/A')}
• 资金费率: {symbol_future_data.get('funding_rate', 'N/A')}
• 24h涨跌: {symbol_future_data.get('change_24h', 'N/A')}%

⏰ {now_shanghai.strftime('%Y-%m-%d %H:%M:%S')} (上海时间)"""

                    print(f"\n{'='*50}")
                    print(f"🚨 {symbol} 触发告警！价差: {diff_display}")
                    print(f"{'='*50}\n")

                    # 发送 Telegram 消息
                    if send_telegram_message(message):
                        last_alert_times[symbol] = current_time


# ==================== 主函数 ====================
def main():
    """主函数"""
    print("="*60)
    print("🤖 多币对现货/合约价差监控系统")
    print("="*60)
    print(f"监控币对: {', '.join(SYMBOLS)}")
    for symbol in SYMBOLS:
        print(f"  • {symbol}: {THRESHOLDS[symbol]}{'%' if USE_PERCENTAGE else ''}")
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
