import time
import json

# pip install websocket_client
from websocket import create_connection

ws = create_connection("wss://api.gateio.ws/ws/v4/")

# 发送订阅请求
ws.send(json.dumps({
    "time": int(time.time()),
    "channel": "spot.tickers",
    "event": "subscribe",
    "payload": ["TSLAX_USDT"]
}))

print("等待价格数据...\n")

# 持续接收消息
try:
    while True:
        result = ws.recv()
        data = json.loads(result)

        # 打印原始消息（调试用）
        # print(json.dumps(data, indent=2))

        # 只处理价格更新消息
        if data.get("event") == "update" and data.get("channel") == "spot.tickers":
            ticker = data["result"]
            print(f"📊 {ticker['currency_pair']}")
            print(f"   最新价格: {ticker['last']}")
            print(f"   24h涨跌: {ticker['change_percentage']}%")
            print(f"   24h最高: {ticker['high_24h']}")
            print(f"   24h最低: {ticker['low_24h']}")
            print(f"   买一价: {ticker['highest_bid']}")
            print(f"   卖一价: {ticker['lowest_ask']}")
            print("-" * 40)
        elif data.get("event") == "subscribe":
            print(f"✅ 订阅成功: {data.get('payload')}\n")

except KeyboardInterrupt:
    print("\n⏹️  停止接收")
    ws.close()