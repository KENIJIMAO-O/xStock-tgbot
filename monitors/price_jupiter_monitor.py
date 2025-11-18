#!/usr/bin/env python3
"""
TSLAx实时价格查询脚本
支持Jupiter Price API和Quote API两种方案
"""

import requests
from typing import Optional, Dict
from datetime import datetime


# 代币地址
TSLAX_MINT = "XsDoVfqeBukxuZHWhdvWHBhgEHjGNst4MLodqsJHzoB"
USDT_MINT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"  # Solana上的USDT

# API端点
JUPITER_PRICE_API = "https://lite-api.jup.ag/price/v3"


class JupiterPriceChecker:
    """Jupiter价格查询器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json'
        })
    
    def get_price_v1(self, token_mint: str, vs_token: str = "USDT") -> Optional[Dict]:
        """
        方案1: 使用Jupiter Price API获取价格
        
        Args:
            token_mint: 目标代币的mint地址
            vs_token: 对标代币符号 (USDT, USDC, SOL等)
        
        Returns:
            包含价格信息的字典
        """
        try:
            params = {
                'ids': token_mint,
                'vsToken': vs_token
            }
            
            response = self.session.get(JUPITER_PRICE_API, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            price_data = data[token_mint]
            stock_data = price_data.get("stockData")
            print("price_data:{}", price_data)
            print("stock_data:{}", stock_data)
            return {
                'symbol': 'TSLAx',
                'method': 'Price API',
                'usd_price': price_data.get('usdPrice'),
                'vs_token': vs_token,
                'id': stock_data.get('id'),
                'price': stock_data.get('price'),
                'timestamp': stock_data.get("updatedAt")
            }

                
        except requests.exceptions.RequestException as e:
            print(f"❌ Price API请求失败: {e}")
            return None
        except Exception as e:
            print(f"❌ Price API处理失败: {e}")
            return None


def print_price_result(result: Optional[Dict], method_name: str):
    """打印价格查询结果"""
    print(f"\n{'='*60}")
    print(f"📊 {method_name}")
    print(f"{'='*60}")
    
    if result is None:
        print("❌ 查询失败")
        return
    
    if result['method'] == 'Price API':
        print(f"✅ 查询成功")
        print(f"代币符号: {result['symbol']}")
        print(f"价格: ${result['price']:.4f} {result['vs_token']}")
        print(f"时间: {result['timestamp']}")
        
    elif result['method'] == 'Quote API':
        print(f"✅ 查询成功")
        print(f"1 TSLAx ≈ ${result['price_per_token']:.4f} USDT")
        print(f"1 USDT ≈ {result['tokens_per_usdt']:.6f} TSLAx")
        print(f"价格影响: {result['price_impact']}")
        print(f"交易路径: {result['route']}")
        print(f"时间: {result['timestamp']}")


def main():
    """主函数"""
    print("🚀 TSLAx实时价格查询工具")
    print(f"代币地址: {TSLAX_MINT}")
    print(f"查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    checker = JupiterPriceChecker()
    
    # 方案1: Price API
    print("\n" + "="*60)
    print("方案1: Jupiter Price API (直接获取价格)")
    print("="*60)
    
    # 先尝试USDT
    result1_usdt = checker.get_price_v1(TSLAX_MINT, vs_token="USDT")
    print_price_result(result1_usdt, "Price API - USDT")
    
    # 总结
    print("\n" + "="*60)
    print("📝 总结")
    print("="*60)
    print("Price API: 快速获取大致价格，适合监控")

if __name__ == "__main__":
    main()