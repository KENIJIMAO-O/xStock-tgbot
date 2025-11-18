"""Base class for exchange WebSocket connectors"""

from abc import ABC, abstractmethod
from typing import List, Callable
import threading


class ExchangeConnector(ABC):
    """Abstract base class for exchange WebSocket connections"""

    def __init__(self, symbols: List[str], on_price_update: Callable):
        """
        Initialize exchange connector

        Args:
            symbols: List of trading pair symbols to monitor
            on_price_update: Callback function(exchange, symbol, price_type, price)
        """
        self.symbols = symbols
        self.on_price_update = on_price_update
        self.running = False
        self.threads = []

    @abstractmethod
    def start_spot_listener(self):
        """Start spot price listener thread"""
        pass

    def start_futures_listener(self):
        """Start futures price listener thread (optional, can be overridden)"""
        pass

    @abstractmethod
    def get_exchange_name(self) -> str:
        """Return exchange name"""
        pass

    def start(self, enable_futures: bool = True):
        """
        Start listeners

        Args:
            enable_futures: Whether to start futures listener (default: True)
        """
        self.running = True

        spot_thread = threading.Thread(target=self.start_spot_listener, daemon=True)
        spot_thread.start()
        self.threads = [spot_thread]

        if enable_futures and hasattr(self, 'start_futures_listener'):
            futures_thread = threading.Thread(target=self.start_futures_listener, daemon=True)
            futures_thread.start()
            self.threads.append(futures_thread)

        listener_types = "spot + futures" if enable_futures else "spot only"
        print(f"✅ {self.get_exchange_name()} connector started ({listener_types}) for {len(self.symbols)} symbols")

    def stop(self):
        """Stop all listeners"""
        self.running = False
        print(f"🛑 {self.get_exchange_name()} connector stopped")
