"""
天气服务模块
负责从 OpenWeatherMap API 获取广州的天气信息
"""

import os
import httpx
import logging

logger = logging.getLogger(__name__)


async def get_guangzhou_weather() -> str | None:
    """
    异步获取广州的当前天气信息

    Returns:
        str: 格式化的天气信息字符串，例如："广州当前天气：晴，气温：25.3°C"
        None: 如果获取失败
    """
    api_key = os.environ.get("WEATHER_API_KEY")

    if not api_key:
        logger.error("WEATHER_API_KEY 未设置")
        return None

    # 去除可能的空格
    api_key = api_key.strip()

    # 调试信息：显示API密钥长度和前4位
    logger.info(f"API密钥长度: {len(api_key)}, 前4位: {api_key[:4]}...")

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": "Guangzhou",
        "appid": api_key,
        "units": "metric",  # 使用摄氏度
        "lang": "zh_cn"     # 中文
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)

            if response.status_code != 200:
                logger.error(f"天气API请求失败，状态码: {response.status_code}")
                logger.error(f"响应内容: {response.text}")
                return None

            data = response.json()

            # 提取天气描述和温度
            description = data["weather"][0]["description"]
            temperature = data["main"]["temp"]

            # 返回格式化的天气信息
            return f"广州当前天气：{description}，气温：{temperature}°C"

    except httpx.TimeoutException:
        logger.error("天气API请求超时")
        return None
    except httpx.RequestError as e:
        logger.error(f"天气API请求错误: {e}")
        return None
    except (KeyError, IndexError) as e:
        logger.error(f"解析天气API响应失败: {e}")
        return None
    except Exception as e:
        logger.error(f"获取天气信息时发生未知错误: {e}")
        return None
