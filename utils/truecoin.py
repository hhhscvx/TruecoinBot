import asyncio
import random
from urllib.parse import quote, unquote

import aiohttp
from aiohttp_socks import ProxyConnector
from pyrogram import Client
from pyrogram.raw.functions.messages import RequestWebView
from pyrogram.raw.types import WebViewResultUrl
from fake_useragent import UserAgent

from utils.core import logger
from data import config


class TrueCoin:
    def __init__(self, tg_client: Client, proxy: str | None = None) -> None:
        self.tg_client = tg_client
        self.session_name = tg_client.name
        self.proxy = f"{config.PROXY_TYPE_REQUESTS}://{proxy}" if proxy else None
        connector = ProxyConnector.from_url(url=self.proxy) if proxy else aiohttp.TCPConnector(verify_ssl=False)

        if proxy:
            proxy = {
                "scheme": config.PROXY_TYPE_TG,
                "hostname": proxy.split(":")[1].split("@")[1],
                "port": int(proxy.split(":")[2]),
                "username": proxy.split(":")[0],
                "password": proxy.split(":")[1].split("@")[0]
            }

        headers = {
            "User-Agent": UserAgent(os='android').random
        }
        self.session = aiohttp.ClientSession(headers=headers, trust_env=True, connector=connector)

    async def logout(self):
        await self.session.close()

    async def login(self):
        await asyncio.sleep(random.uniform(*config.DELAY_CONN_ACCOUNT))
        query = await self.get_tg_web_data()

        if query is None:
            logger.error(f"{self.session_name} | Session {self.session_name}.session invalid")
            await self.logout()
            return

        self.client_tg_id = int(unquote(query).split('user={"id":', maxsplit=1)[1].split(',"first_name"', maxsplit=1)[0])

        json_data = {
            "lang": "en",
            "tgPlatform": "android",
            "tgVersion": "7.10",
            "tgWebAppStartParam": None,
            "userId": self.client_tg_id
        }
        self.session.headers["Query"] = query
        resp = await self.session.post(url='https://api.true.world/api/auth/signIn',
                                       json=json_data)
        resp_json = await resp.json()
        user = resp_json['user']
        logger.success(
            f"{self.session_name} | Successfully sign in! Coins: {user['coins']}; Spins: {user['currentSpins']}")
        self.session.headers['Authorization'] = 'Bearer ' + resp_json['token']
        return True

    async def user_stats(self):
        resp = await self.session.get('https://api.true.world/api/game/getUserAchives')
        resp_json = await resp.json()

        return resp_json['user'] if resp.status == 200 else None

    async def collect_daily_reward(self) -> dict[str, int]:
        resp = await self.session.get('https://api.true.world/api/dailyReward/collectReward')
        resp_json = await resp.json()

        return {
            'coins': resp_json['user']['coins'],
            'day': resp_json['reward']['rewardId']
        } if resp.status == 200 else None

    async def get_wall_tasks(self) -> list[dict]:
        resp = await self.session.get('https://api.true.world/api/ad/getWallFeed')
        resp_json = await resp.json()
        return resp_json

    async def complete_wall_task(self, task_id: int) -> str:
        resp = await self.session.get(f'https://api.true.world/api/ad/getWallClick/{task_id}')
        resp_json = await resp.json()

        return resp_json  # OK

    async def roll(self) -> tuple[str]:
        await asyncio.sleep(random.uniform(*config.DELAY_BETWEEN_ROLL))

        resp = await self.session.get('https://api.true.world/api/game/roll')
        resp_json = await resp.json()

        result = resp_json['result']
        winType = result['winType']
        match winType:
            case 'coins':
                coins = result['coins']
                spins = 0
            case 'spins':
                spins = result['spins']
                coins = 0
            case _:
                coins, spins = 0, 0

        return {
            'winType': winType,
            'coins': coins,
            'spins': spins,
            'user_coins': resp_json['user']['coins'],
            'user_spins': resp_json['user']['currentSpins']
        }

    async def earn_partner_task(self, task_id: int) -> bool:
        resp = await self.session.post('https://api.true.world/api/partners/earnPartnerTask',
                                       json={'taskId': task_id})
        resp_json = await resp.json()

        try:
            earned = resp_json['status'] == True
        except:
            earned = False

        return earned

    async def get_partner_tasks(self):
        resp = await self.session.get('https://api.true.world/api/partners/getPartnersGroupsOfTasks')
        resp_json = await resp.json()

        return resp_json

    async def get_tg_web_data(self):
        try:
            await self.tg_client.connect()
            await self.tg_client.send_message('true_coin_bot', '/start')
            await asyncio.sleep(random.uniform(1.5, 2))

            web_view: WebViewResultUrl = await self.tg_client.invoke(RequestWebView(
                peer=await self.tg_client.resolve_peer('true_coin_bot'),
                bot=await self.tg_client.resolve_peer('true_coin_bot'),
                platform="android",
                from_bot_menu=False,
                url="https://bot.true.world/"
            ))
            await self.tg_client.disconnect()
            auth_url = web_view.url

            query = unquote(string=unquote(string=auth_url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0]))
            query_id = query.split('query_id=')[1].split('&user=')[0]
            user = quote(query.split("&user=")[1].split('&auth_date=')[0])
            auth_date = query.split('&auth_date=')[1].split('&hash=')[0]
            hash_ = query.split('&hash=')[1]

            return f"query_id={query_id}&user={user}&auth_date={auth_date}&hash={hash_}"
        except Exception as err:
            return
