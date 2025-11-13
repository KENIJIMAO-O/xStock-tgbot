import time
import json
from websocket import create_connection

# 永续合约 WebSocket 连接
# 测试网: wss://fx-ws-testnet.gateio.ws/v4/ws/btc
# 正式网: wss://fx-ws.gateio.ws/v4/ws/btc (BTC结算) 或 /usdt (USDT结算)
ws = create_connection("wss://fx-ws.gateio.ws/v4/ws/usdt")

# 发送订阅请求
subscribe_msg = {
    "time": int(time.time()),
    "channel": "futures.tickers",
    "event": "subscribe",
    "payload": ["AAPLX_USDT"]  # 永续合约币对
}

ws.send(json.dumps(subscribe_msg))
print("等待永续合约价格数据...\n")

# 持续接收消息
try:
    while True:
        result = ws.recv()
        data = json.loads(result)

        # 打印原始消息（调试用）
        # print(json.dumps(data, indent=2))

        # 只处理价格更新消息
        if data.get("event") == "update" and data.get("channel") == "futures.tickers":
            # result 是一个数组，需要遍历
            tickers = data["result"]

            for ticker in tickers:
                print(f"📊 永续合约: {ticker['contract']}")
                print(f"   最新价格: {ticker.get('last', 'N/A')}")
                print(f"   标记价格: {ticker.get('mark_price', 'N/A')}")
                print(f"   指数价格: {ticker.get('index_price', 'N/A')}")
                print(f"   24h涨跌: {ticker.get('change_percentage', 'N/A')}%")
                print(f"   24h最高: {ticker.get('high_24h', 'N/A')}")
                print(f"   24h最低: {ticker.get('low_24h', 'N/A')}")
                print(f"   24h成交量: {ticker.get('volume_24h', 'N/A')}")
                print(f"   资金费率: {ticker.get('funding_rate', 'N/A')}")
                print(f"   持仓量: {ticker.get('total_size', 'N/A')}")
                print("-" * 50)

        elif data.get("event") == "subscribe":
            print(f"✅ 订阅成功: {data.get('payload')}\n")
        elif data.get("event") == "error":
            print(f"❌ 错误: {data}")
            break

except KeyboardInterrupt:
    print("\n⏹️  停止接收")
    ws.close()
except Exception as e:
    print(f"❌ 发生错误: {e}")
    ws.close()