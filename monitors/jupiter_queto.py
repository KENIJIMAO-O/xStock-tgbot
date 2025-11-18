#!/usr/bin/env python3
"""
TSLAx价格计算器 - 交互式CLI工具
可以输入任意数量的TSLAx，立即计算能换多少USDT
"""

import requests
import sys
from typing import Optional, Tuple


TSLAX_MINT = "XsDoVfqeBukxuZHWhdvWHBhgEHjGNst4MLodqsJHzoB"
USDT_MINT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
JUPITER_QUOTE_API = "https://lite-api.jup.ag/swap/v1/quote"

TSLAX_DECIMALS = 8
USDT_DECIMALS = 6


def calculate_tslax_to_usdt(tslax_amount: float) -> Optional[Tuple[float, dict]]:
    """
    计算指定数量的TSLAx能换多少USDT
    
    Args:
        tslax_amount: TSLAx数量（人类可读，如 1.5）
    
    Returns:
        (usdt_amount, details) 或 None
    """
    try:
        # 转换为最小单位
        amount_raw = int(tslax_amount * (10 ** TSLAX_DECIMALS))
        
        if amount_raw <= 0:
            print("❌ 数量必须大于0")
            return None
        
        # 调用API
        params = {
            'inputMint': TSLAX_MINT,
            'outputMint': USDT_MINT,
            'amount': amount_raw,
            'slippageBps': 50
        }
        
        response = requests.get(JUPITER_QUOTE_API, params=params, timeout=10)
        response.raise_for_status()
        
        quote = response.json()
        
        if 'outAmount' not in quote:
            print("❌ API返回格式错误")
            return None
        
        # 解析结果
        in_amount = int(quote['inAmount'])
        out_amount = int(quote['outAmount'])
        
        # 转换为人类可读
        actual_tslax = in_amount / (10 ** TSLAX_DECIMALS)
        actual_usdt = out_amount / (10 ** USDT_DECIMALS)
        
        # 计算单价
        unit_price = actual_usdt / actual_tslax if actual_tslax > 0 else 0
        
        # 提取路由
        route = []
        if 'routePlan' in quote:
            for step in quote['routePlan']:
                if 'swapInfo' in step:
                    route.append(step['swapInfo'].get('label', 'Unknown'))
        
        details = {
            'actual_tslax': actual_tslax,
            'actual_usdt': actual_usdt,
            'unit_price': unit_price,
            'price_impact': quote.get('priceImpactPct', 'N/A'),
            'route': ' -> '.join(route) if route else 'Unknown'
        }
        
        return actual_usdt, details
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求失败: {e}")
        return None
    except Exception as e:
        print(f"❌ 计算失败: {e}")
        return None


def calculate_usdt_to_tslax(usdt_amount: float) -> Optional[Tuple[float, dict]]:
    """
    计算指定数量的USDT能换多少TSLAx
    
    Args:
        usdt_amount: USDT数量（人类可读，如 100.5）
    
    Returns:
        (tslax_amount, details) 或 None
    """
    try:
        # 转换为最小单位
        amount_raw = int(usdt_amount * (10 ** USDT_DECIMALS))
        
        if amount_raw <= 0:
            print("❌ 数量必须大于0")
            return None
        
        # 调用API（反向查询）
        params = {
            'inputMint': USDT_MINT,
            'outputMint': TSLAX_MINT,
            'amount': amount_raw,
            'slippageBps': 50
        }
        
        response = requests.get(JUPITER_QUOTE_API, params=params, timeout=10)
        response.raise_for_status()
        
        quote = response.json()
        
        if 'outAmount' not in quote:
            print("❌ API返回格式错误")
            return None
        
        # 解析结果
        in_amount = int(quote['inAmount'])
        out_amount = int(quote['outAmount'])
        
        # 转换为人类可读
        actual_usdt = in_amount / (10 ** USDT_DECIMALS)
        actual_tslax = out_amount / (10 ** TSLAX_DECIMALS)
        
        # 计算单价
        unit_price = actual_usdt / actual_tslax if actual_tslax > 0 else 0
        
        # 提取路由
        route = []
        if 'routePlan' in quote:
            for step in quote['routePlan']:
                if 'swapInfo' in step:
                    route.append(step['swapInfo'].get('label', 'Unknown'))
        
        details = {
            'actual_usdt': actual_usdt,
            'actual_tslax': actual_tslax,
            'unit_price': unit_price,
            'price_impact': quote.get('priceImpactPct', 'N/A'),
            'route': ' -> '.join(route) if route else 'Unknown'
        }
        
        return actual_tslax, details
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求失败: {e}")
        return None
    except Exception as e:
        print(f"❌ 计算失败: {e}")
        return None


def interactive_mode():
    """交互式模式"""
    print("=" * 70)
    print("💰 TSLAx价格计算器 - 交互式模式")
    print("=" * 70)
    print("功能:")
    print("  1. 输入TSLAx数量，计算能换多少USDT")
    print("  2. 输入USDT数量（带u后缀），计算能换多少TSLAx")
    print("\n示例:")
    print("  > 1         # 1 TSLAx能换多少USDT")
    print("  > 0.5       # 0.5 TSLAx能换多少USDT")
    print("  > 100u      # 100 USDT能换多少TSLAx")
    print("  > quit      # 退出")
    print("=" * 70)
    
    while True:
        try:
            user_input = input("\n💵 请输入数量 (或'quit'退出): ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 再见！")
                break
            
            if not user_input:
                continue
            
            # 检查是否是USDT查询（以u结尾）
            if user_input.lower().endswith('u'):
                # USDT -> TSLAx
                try:
                    usdt_amount = float(user_input[:-1])
                except ValueError:
                    print("❌ 无效的数量格式")
                    continue
                
                print(f"\n⏳ 正在查询 {usdt_amount} USDT 能换多少 TSLAx...")
                result = calculate_usdt_to_tslax(usdt_amount)
                
                if result:
                    tslax_amount, details = result
                    print("\n" + "=" * 70)
                    print("✅ 查询结果:")
                    print(f"   {details['actual_usdt']:.6f} USDT → {details['actual_tslax']:.9f} TSLAx")
                    print(f"   单价: 1 TSLAx ≈ ${details['unit_price']:.4f} USDT")
                    print(f"   价格影响: {details['price_impact']}")
                    print(f"   交易路径: {details['route']}")
                    print("=" * 70)
            else:
                # TSLAx -> USDT
                try:
                    tslax_amount = float(user_input)
                except ValueError:
                    print("❌ 无效的数量格式")
                    continue
                
                print(f"\n⏳ 正在查询 {tslax_amount} TSLAx 能换多少 USDT...")
                result = calculate_tslax_to_usdt(tslax_amount)
                
                if result:
                    usdt_amount, details = result
                    print("\n" + "=" * 70)
                    print("✅ 查询结果:")
                    print(f"   {details['actual_tslax']:.9f} TSLAx → {details['actual_usdt']:.6f} USDT")
                    print(f"   单价: 1 TSLAx ≈ ${details['unit_price']:.4f} USDT")
                    print(f"   价格影响: {details['price_impact']}")
                    print(f"   交易路径: {details['route']}")
                    print("=" * 70)
        
        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            print(f"❌ 错误: {e}")


def cli_mode(amount_str: str):
    """命令行模式"""
    try:
        if amount_str.lower().endswith('u'):
            # USDT -> TSLAx
            usdt_amount = float(amount_str[:-1])
            result = calculate_usdt_to_tslax(usdt_amount)
            
            if result:
                tslax_amount, details = result
                print(f"{details['actual_usdt']:.6f} USDT → {details['actual_tslax']:.9f} TSLAx")
                print(f"单价: 1 TSLAx = ${details['unit_price']:.4f}")
        else:
            # TSLAx -> USDT
            tslax_amount = float(amount_str)
            result = calculate_tslax_to_usdt(tslax_amount)
            
            if result:
                usdt_amount, details = result
                print(f"{details['actual_tslax']:.9f} TSLAx → {details['actual_usdt']:.6f} USDT")
                print(f"单价: 1 TSLAx = ${details['unit_price']:.4f}")
    
    except ValueError:
        print(f"❌ 无效的数量: {amount_str}")
        sys.exit(1)


def main():
    """主函数"""
    if len(sys.argv) > 1:
        # 命令行模式
        cli_mode(sys.argv[1])
    else:
        # 交互式模式
        interactive_mode()


if __name__ == "__main__":
    main()