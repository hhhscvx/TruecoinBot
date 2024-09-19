
import asyncio
from pprint import pprint
import random

from pyrogram import Client

from data import config
from utils.truecoin import TrueCoin
from utils.core import logger


async def start(tg_client: Client, proxy: str | None = None):
    truecoin = TrueCoin(tg_client=tg_client, proxy=proxy)
    session_name = tg_client.name

    if await truecoin.login():
        while True:
            try:
                if stats := await truecoin.user_stats():
                    logger.info(
                        f"{session_name} | Balance: {stats['coins']} | Spins: {stats['currentSpins']}/{stats['maxSpins']}")
                else:
                    logger.error(f'{session_name} | Error when get user statistics')

                collect_daily = await truecoin.collect_daily_reward()
                if collect_daily:
                    logger.success(
                        f"{session_name} | Claimed daily reward; Day {collect_daily['day']} |  Balance: {collect_daily['coins']}")
                    await asyncio.sleep(2)

                partner_tasks = await truecoin.get_partner_tasks()
                pprint(partner_tasks)
                await asyncio.sleep(1)
                for partner in partner_tasks:
                    for task in partner['tasks']:
                        pprint(task)
                        if task['active'] is True:
                            is_completed = await truecoin.earn_partner_task(task_id=task['id'])
                            if is_completed:
                                logger.success(
                                    f"{session_name} | Completed task by {partner['name']}; Earned: «{task['content']}»")
                                await asyncio.sleep(random.uniform(0.8, 1.25))

                wall_tasks = await truecoin.get_wall_tasks()
                for task in wall_tasks:
                    if task['isDone'] is False:
                        res = await truecoin.complete_wall_task(task_id=task['id'])
                        if res == "OK":
                            logger.success(f"session_name | Completed wall task «{task['name']}»")

                while True:
                    roll = await truecoin.roll()
                    win_type = roll['winType']
                    earned = f"{roll['coins']} coins" if win_type == 'coins' else f"{roll['spins']} spins"
                    logger.success(f"{session_name} | Successfully spinned! Slots: {roll['slots']} | Win type: {win_type} "
                                   f"+{earned} | "
                                   f"Balance: {roll['user_coins']} coins | {roll['user_spins']} spins")
                    if roll['user_spins'] < 5:
                        await asyncio.sleep(random.uniform(*config.DELAY_BY_FEW_SPINS_LEFT))
                        break

            except Exception as err:
                logger.error(f"{session_name} | Unknown error: {err}")

    else:
        await truecoin.logout()