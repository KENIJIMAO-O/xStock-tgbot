"""Gate.io WebSocket connector"""

import json
import time
from websocket import create_connection
from .base import ExchangeConnector


class GateIOConnector(ExchangeConnector):
    """Gate.io exchange WebSocket connector"""

    SPOT_WS_URL = "wss://api.gateio.ws/ws/v4/"
    FUTURES_WS_URL = "wss://fx-ws.gateio.ws/v4/ws/usdt"

    def get_exchange_name(self) -> str:
        return "Gate.io"

    def start_spot_listener(self):
        """监听 Gate.io 现货价格"""
        print(f"🟢 启动 Gate.io 现货监听: {', '.join(self.symbols)}")

        while self.running:
            try:
                ws = create_connection(self.SPOT_WS_URL)
                ws.send(json.dumps({
                    "time": int(time.time()),
                    "channel": "spot.tickers",
                    "event": "subscribe",
                    "payload": self.symbols
                }))

                while self.running:
                    result = ws.recv()
                    data = json.loads(result)

                    if data.get("event") == "update" and data.get("channel") == "spot.tickers":
                        ticker = data["result"]
                        symbol = ticker["currency_pair"]

                        if symbol in self.symbols:
                            price = float(ticker["last"])
                            extra_data = {
                                "change_24h": ticker.get("change_percentage", "N/A"),
                                "high_24h": ticker.get("high_24h", "N/A"),
                                "low_24h": ticker.get("low_24h", "N/A"),
                                "volume_24h": ticker.get("quote_volume", "N/A"),
                            }

                            self.on_price_update(
                                exchange="gateio",
                                symbol=symbol,
                                price_type="spot",
                                price=price,
                                extra_data=extra_data
                            )

                ws.close()

            except Exception as e:
                print(f"❌ Gate.io 现货连接错误: {e}，5秒后重连...")
                time.sleep(5)

    def start_futures_listener(self):
        """监听 Gate.io 合约价格"""
        print(f"🔵 启动 Gate.io 合约监听: {', '.join(self.symbols)}")

        while self.running:
            try:
                ws = create_connection(self.FUTURES_WS_URL)
                ws.send(json.dumps({
                    "time": int(time.time()),
                    "channel": "futures.tickers",
                    "event": "subscribe",
                    "payload": self.symbols
                }))

                while self.running:
                    result = ws.recv()
                    data = json.loads(result)

                    if data.get("event") == "update" and data.get("channel") == "futures.tickers":
                        tickers = data["result"]

                        for ticker in tickers:
                            symbol = ticker["contract"]

                            if symbol in self.symbols:
                                price = float(ticker["last"])
                                extra_data = {
                                    "mark_price": ticker.get("mark_price", "N/A"),
                                    "index_price": ticker.get("index_price", "N/A"),
                                    "funding_rate": ticker.get("funding_rate", "N/A"),
                                    "change_24h": ticker.get("change_percentage", "N/A"),
                                    "high_24h": ticker.get("high_24h", "N/A"),
                                    "low_24h": ticker.get("low_24h", "N/A"),
                                    "volume_24h": ticker.get("volume_24h", "N/A"),
                                }

                                self.on_price_update(
                                    exchange="gateio",
                                    symbol=symbol,
                                    price_type="futures",
                                    price=price,
                                    extra_data=extra_data
                                )

                ws.close()

            except Exception as e:
                print(f"❌ Gate.io 合约连接错误: {e}，5秒后重连...")
                time.sleep(5)
