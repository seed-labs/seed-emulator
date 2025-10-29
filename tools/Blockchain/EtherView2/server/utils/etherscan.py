import re
import aiohttp
import asyncio
import requests


class EtherScan(object):
    @staticmethod
    async def get_home_data():
        url = 'https://goto.etherscan.com/'
        ether_price = gas_price = market_cap = -1
        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        }
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url) as resp:
                    resp.raise_for_status()  # 若状态码非 2xx，会抛异常
                    html_text = await resp.text()
            pattern = re.compile(
                r"<a href='/chart/etherprice'>(.*?)</a>.*?<span class='gasPricePlaceHolder'>(.*?)</span>.*?<span id='data-mcap'>(.*?)</span>",
                re.S)
            ret = re.findall(pattern, html_text)
            if ret:
                ether_price, gas_price, market_cap = ret[0][0], f"{ret[0][1]} Gwei", ret[0][2]
        except Exception as e:
            print(e)

        return {
            'etherPrice': ether_price,
            'gasPrice': gas_price,
            'marketCap': market_cap,
        }
