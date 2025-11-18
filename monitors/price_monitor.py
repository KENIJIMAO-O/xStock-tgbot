"""
多交易所分级价差监控系统
监控 Gate.io 合约价格 vs 所有交易所现货价格
⚠️ WARN: 1个交易所超阈值
🚨 EMERGENCY: 2个或更多交易所超阈值
"""

import time
import threading
import os
from datetime import datetime
from typing import Dict, Any, List
import pytz
from dotenv import load_dotenv
import requests

from .exchanges.gateio import GateIOConnector
from .exchanges.bybit import BybitConnector

# 加载环境变量
load_dotenv()

# ==================== 配置 ====================
# 交易所配置
EXCHANGES_STR = os.environ.get("EXCHANGES", "gateio")
ENABLED_EXCHANGES = [e.strip().lower() for e in EXCHANGES_STR.split(",")]

# 监控币对（所有交易所共享）
SYMBOLS_STR = os.environ.get("MONITOR_SYMBOLS", "TSLAX_USDT")
SYMBOLS = [s.strip() for s in SYMBOLS_STR.split(",")]

# 通用配置
PRICE_DIFF_THRESHOLD = float(os.environ.get("PRICE_DIFF_THRESHOLD", "0.5"))
USE_PERCENTAGE = os.environ.get("USE_PERCENTAGE", "True").lower() == "true"
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "1"))

# 分级冷却时间
WARN_COOLDOWN = int(os.environ.get("WARN_COOLDOWN", "300"))
EMERGENCY_COOLDOWN = int(os.environ.get("EMERGENCY_COOLDOWN", "180"))

# Telegram 配置
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")

# ==================== 全局变量 ====================
# Gate.io 合约价格（唯一来源）
gateio_futures: Dict[str, float] = {}
futures_data: Dict[str, Dict[str, Any]] = {}

# 所有交易所现货价格
all_spot_prices: Dict[str, Dict[str, float]] = {}  # {exchange: {symbol: price}}
spot_data: Dict[str, Dict[str, Dict[str, Any]]] = {}  # {exchange: {symbol: {...}}}

# 分级冷却时间
last_alert_times: Dict[str, Dict[str, float]] = {}  # {symbol: {"WARN": ts, "EMERGENCY": ts}}

# 初始化数据结构
for exchange in ENABLED_EXCHANGES:
    all_spot_prices[exchange] = {}
    spot_data[exchange] = {}

for symbol in SYMBOLS:
    last_alert_times[symbol] = {"WARN": 0, "EMERGENCY": 0}

lock = threading.Lock()  # 线程锁


# ==================== Telegram 推送函数 ====================
def send_telegram_message(message: str) -> bool:
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


# ==================== 价格更新回调 ====================
def on_price_update(exchange: str, symbol: str, price_type: str, price: float, extra_data: Dict[str, Any]):
    """
    价格更新回调函数

    Args:
        exchange: 交易所名称 (gateio, bybit)
        symbol: 币对 (TSLAX_USDT)
        price_type: 价格类型 (spot, futures)
        price: 价格
        extra_data: 额外数据
    """
    with lock:
        if exchange == "gateio" and price_type == "futures":
            # Gate.io 合约价格
            gateio_futures[symbol] = price
            futures_data[symbol] = extra_data
            print(f"📊 Gate.io 合约 {symbol}: {price}")
        elif price_type == "spot":
            # 所有交易所现货价格
            if exchange in all_spot_prices:
                all_spot_prices[exchange][symbol] = price
                spot_data[exchange][symbol] = extra_data
                print(f"📊 {exchange.upper()} 现货 {symbol}: {price}")


# ==================== 分级告警消息生成 ====================
def generate_alert_message(
    symbol: str,
    futures_price: float,
    exceeded_list: List[Dict[str, Any]],
    alert_level: str
) -> str:
    """
    生成分级告警消息

    Args:
        symbol: 币对
        futures_price: Gate.io 合约价格
        exceeded_list: 超阈值的交易所列表
        alert_level: 告警级别 (WARN/EMERGENCY)

    Returns:
        格式化的告警消息
    """
    shanghai_tz = pytz.timezone('Asia/Shanghai')
    now_shanghai = datetime.now(shanghai_tz)

    # 级别emoji和标题
    if alert_level == "EMERGENCY":
        level_emoji = "🚨🚨"
        level_text = "紧急价差告警"
    else:
        level_emoji = "⚠️"
        level_text = "价差警告"

    # 基本信息
    message = f"""{level_emoji} <b>{level_text}</b>

<b>币对:</b> {symbol}
<b>Gate.io 合约:</b> ${futures_price:.2f}

<b>异常交易所 ({len(exceeded_list)}个):</b>
"""

    # 添加每个交易所的详情
    total_diff_pct = 0.0
    max_diff_pct = 0.0
    max_diff_exchange = ""

    for item in exceeded_list:
        exchange = item["exchange"]
        spot_price = item["spot_price"]
        diff = item["diff"]
        diff_pct = item["diff_pct"]

        total_diff_pct += abs(diff_pct)
        if abs(diff_pct) > abs(max_diff_pct):
            max_diff_pct = diff_pct
            max_diff_exchange = exchange

        if USE_PERCENTAGE:
            diff_display = f"{diff_pct:+.2f}%"
        else:
            diff_display = f"{diff:+.4f}"

        message += f"📊 <b>{exchange.upper()}</b> 现货: ${spot_price:.2f}\n"
        message += f"   价差: {diff_display}\n\n"

    # EMERGENCY 级别显示统计信息
    if alert_level == "EMERGENCY":
        avg_diff_pct = total_diff_pct / len(exceeded_list)
        message += f"<b>平均价差:</b> {avg_diff_pct:.2f}%\n"
        message += f"<b>最大价差:</b> {abs(max_diff_pct):.2f}% ({max_diff_exchange.upper()})\n\n"

    # 合约详细信息（如果有）
    if symbol in futures_data:
        fd = futures_data[symbol]
        message += f"""<b>Gate.io 合约详情:</b>
• 标记价格: ${fd.get('mark_price', 'N/A')}
• 指数价格: ${fd.get('index_price', 'N/A')}
• 资金费率: {fd.get('funding_rate', 'N/A')}

"""

    message += f"⏰ {now_shanghai.strftime('%Y-%m-%d %H:%M:%S')} (上海时间)"

    return message


# ==================== 价差监控线程 ====================
def price_monitor():
    """监控价差并发送分级告警"""
    print(f"⚡ 启动分级价差监控")
    print(f"   监控币对: {', '.join(SYMBOLS)}")
    print(f"   交易所: {', '.join(ENABLED_EXCHANGES)}")
    print(f"   价差阈值: {PRICE_DIFF_THRESHOLD}{'%' if USE_PERCENTAGE else ''}")
    print(f"   WARN 冷却: {WARN_COOLDOWN}秒")
    print(f"   EMERGENCY 冷却: {EMERGENCY_COOLDOWN}秒\n")

    while True:
        time.sleep(CHECK_INTERVAL)

        # 遍历所有币对
        for symbol in SYMBOLS:
            with lock:
                # 检查 Gate.io 合约价格是否已接收
                if symbol not in gateio_futures:
                    continue

                futures_price = gateio_futures[symbol]

            # 统计超过阈值的交易所
            exceeded_exchanges = []

            for exchange in ENABLED_EXCHANGES:
                with lock:
                    if symbol not in all_spot_prices.get(exchange, {}):
                        continue

                    spot_price = all_spot_prices[exchange][symbol]

                # 计算价差
                price_diff = futures_price - spot_price

                if USE_PERCENTAGE:
                    price_diff_pct = (price_diff / spot_price) * 100
                    current_value = abs(price_diff_pct)
                else:
                    price_diff_pct = (price_diff / spot_price) * 100  # 用于显示
                    current_value = abs(price_diff)

                # 显示当前价差
                if USE_PERCENTAGE:
                    diff_display = f"{price_diff_pct:+.2f}%"
                else:
                    diff_display = f"{price_diff:+.4f}"

                print(f"💹 {symbol} | Gate合约: {futures_price:.2f} vs {exchange.upper()}现货: {spot_price:.2f} = {diff_display}")

                # 检查是否超过阈值
                if current_value >= PRICE_DIFF_THRESHOLD:
                    exceeded_exchanges.append({
                        "exchange": exchange,
                        "spot_price": spot_price,
                        "diff": price_diff,
                        "diff_pct": price_diff_pct
                    })

            # 确定告警级别
            num_exceeded = len(exceeded_exchanges)

            if num_exceeded == 0:
                continue  # 无告警
            elif num_exceeded == 1:
                alert_level = "WARN"
                cooldown = WARN_COOLDOWN
            else:  # >= 2
                alert_level = "EMERGENCY"
                cooldown = EMERGENCY_COOLDOWN

            # 检查冷却时间
            current_time = time.time()
            last_time = last_alert_times[symbol][alert_level]

            # 告警升级逻辑：如果从 WARN 升级到 EMERGENCY，立即发送
            is_upgrade = False
            if alert_level == "EMERGENCY":
                last_warn_time = last_alert_times[symbol]["WARN"]
                # 如果最近发送了 WARN，且现在升级为 EMERGENCY
                if last_warn_time > last_time and (current_time - last_warn_time) < WARN_COOLDOWN:
                    is_upgrade = True

            if is_upgrade or (current_time - last_time >= cooldown):
                # 生成告警消息
                message = generate_alert_message(symbol, futures_price, exceeded_exchanges, alert_level)

                print(f"\n{'='*50}")
                if is_upgrade:
                    print(f"📈 {symbol} 告警升级！WARN → EMERGENCY")
                print(f"{alert_level} 触发告警！{num_exceeded}个交易所超阈值")
                print(f"{'='*50}\n")

                # 发送 Telegram 消息
                if send_telegram_message(message):
                    last_alert_times[symbol][alert_level] = current_time


# ==================== 主函数 ====================
def main():
    """主函数"""
    print("="*60)
    print("🤖 多交易所分级价差监控系统")
    print("="*60)
    print(f"监控币对: {', '.join(SYMBOLS)}")
    print(f"交易所: {', '.join(ENABLED_EXCHANGES)}")
    print(f"价差阈值: {PRICE_DIFF_THRESHOLD}{'%' if USE_PERCENTAGE else ''}")
    print(f"WARN 冷却: {WARN_COOLDOWN}秒")
    print(f"EMERGENCY 冷却: {EMERGENCY_COOLDOWN}秒")
    print("="*60 + "\n")

    # 检查配置
    if not BOT_TOKEN or not ADMIN_CHAT_ID:
        print("⚠️  警告: 未配置 Telegram，将只打印告警，不发送通知")
        print("   请在 .env 文件中配置 BOT_TOKEN 和 ADMIN_CHAT_ID\n")

    # 创建并启动所有交易所连接器
    connectors = []

    if "gateio" in ENABLED_EXCHANGES:
        print("📡 启动 Gate.io 连接器（现货 + 合约）...")
        gateio = GateIOConnector(SYMBOLS, on_price_update)
        gateio.start(enable_futures=True)  # 启用合约监听
        connectors.append(gateio)

    if "bybit" in ENABLED_EXCHANGES:
        print("📡 启动 Bybit 连接器（仅现货）...")
        bybit = BybitConnector(SYMBOLS, on_price_update)
        bybit.start(enable_futures=False)  # 禁用合约监听
        connectors.append(bybit)

    # 启动价差监控线程
    print("\n📡 启动价差监控线程...")
    monitor_thread = threading.Thread(target=price_monitor, daemon=True, name="Monitor")
    monitor_thread.start()

    print("\n✅ 所有服务已启动，监控中...\n")

    # 保持主线程运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n⏹️  停止监控")
        for connector in connectors:
            connector.stop()


if __name__ == "__main__":
    main()
