import discord
from discord.ext import commands
import os
import sys
import logging
from datetime import date
from dotenv import load_dotenv
from orm import SteamMetaData, init_database, db_session
from cog import UserCog, ServerCog
from steamapi import SteamAPI
import asyncio
import traceback


load_dotenv()


class Filter(object):
    def __init__(self, level):
        self.__level = level

    def filter(self, logRecord):
        return logRecord.levelno <= self.__level


class WhatShouldWePlayBot(commands.Bot):
    # These are the member id's for the bots, we ignore them for specific checks
    _MEMBER_IGNORE_LIST = [959263650701508638, 961433803484712960]
    _ignore_banlist = False
    api: SteamAPI = SteamAPI(os.getenv("API_KEY"))

    def __init__(self, db_path: str = ":memory:"):
        super().__init__(command_prefix="$", intents=discord.Intents.all())
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(logging.INFO)
        stream_handler.addFilter(Filter(logging.INFO))
        file_handler = logging.FileHandler(f"{date.today()}.log")

        logging.basicConfig(
            format="%(asctime)s [%(levelname)s] %(message)s",
            level=logging.INFO,
            handlers=[stream_handler, file_handler],
        )

        init_database(db_path)

    def sync_with_steam(self):
        games = self.api.get_app_list()
        with db_session:
            SteamMetaData.add_games(games)

    async def on_ready(self):
        logging.info(f"Logged in as user {self.user.name}")

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandInvokeError):
        # For now, lets just dump the exception we get to the console
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)


async def main():
    bot = WhatShouldWePlayBot(os.getenv("DB_PATH"))
    await bot.add_cog(UserCog(bot))
    await bot.add_cog(ServerCog(bot))
    bot.sync_with_steam()
    await bot.start(os.getenv("TOKEN"))


if __name__ == "__main__":
    asyncio.run(main())
