"""Bybit WebSocket connector"""

import json
import time
from websocket import create_connection
from .base import ExchangeConnector


class BybitConnector(ExchangeConnector):
    """Bybit exchange WebSocket connector (spot only)"""

    SPOT_WS_URL = "wss://stream.bybit.com/v5/public/spot"

    def get_exchange_name(self) -> str:
        return "Bybit"

    def _convert_symbol_format(self, symbol: str) -> str:
        """
        Convert symbol from Gate.io format to Bybit format
        Gate.io: TSLAX_USDT -> Bybit: TSLAXUSDT
        """
        return symbol.replace("_", "")

    def start_spot_listener(self):
        """监听 Bybit 现货价格"""
        print(f"🟢 启动 Bybit 现货监听: {', '.join(self.symbols)}")

        # Convert symbols to Bybit format
        bybit_symbols = [self._convert_symbol_format(s) for s in self.symbols]

        while self.running:
            try:
                ws = create_connection(self.SPOT_WS_URL)

                # Subscribe to tickers for all symbols
                subscribe_args = [f"tickers.{symbol}" for symbol in bybit_symbols]
                ws.send(json.dumps({
                    "op": "subscribe",
                    "args": subscribe_args
                }))

                while self.running:
                    result = ws.recv()
                    data = json.loads(result)

                    # Check if this is a ticker update
                    if data.get("topic", "").startswith("tickers."):
                        ticker_data = data.get("data", {})
                        bybit_symbol = ticker_data.get("symbol", "")

                        # Convert back to standard format (TSLAXUSDT -> TSLAX_USDT)
                        # Try to match with original symbols
                        original_symbol = None
                        for orig, bybit in zip(self.symbols, bybit_symbols):
                            if bybit == bybit_symbol:
                                original_symbol = orig
                                break

                        if original_symbol:
                            price = float(ticker_data.get("lastPrice", 0))
                            extra_data = {
                                "change_24h": ticker_data.get("price24hPcnt", "N/A"),
                                "high_24h": ticker_data.get("highPrice24h", "N/A"),
                                "low_24h": ticker_data.get("lowPrice24h", "N/A"),
                                "volume_24h": ticker_data.get("volume24h", "N/A"),
                            }

                            self.on_price_update(
                                exchange="bybit",
                                symbol=original_symbol,
                                price_type="spot",
                                price=price,
                                extra_data=extra_data
                            )

                ws.close()

            except Exception as e:
                print(f"❌ Bybit 现货连接错误: {e}，5秒后重连...")
                time.sleep(5)
