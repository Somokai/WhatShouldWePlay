import discord
import json
import os
import sys
import logging
from datetime import date
from os.path import isfile
from dotenv import load_dotenv

load_dotenv()


class Filter(object):
    def __init__(self, level):
        self.__level = level

    def filter(self, logRecord):
        return logRecord.levelno <= self.__level


class Player(object):
    _RECORD_BASE_PATH = os.getenv("RECORD_BASE_PATH", "")
    _TEMPLATE = {"games": [], "blacklist": []}

    def __init__(self, user):
        self.user = user
        self.record = Player._load_record(f"{Player._RECORD_BASE_PATH}{user.id}.json")

    def _load_record(path):
        if not isfile(path):
            return Player._create_record(path)
        else:
            with open(path, "r+") as json_file:
                return json.load(json_file)

    def _create_record(path):
        with open(path, "a") as json_record:
            json.dump(Player._TEMPLATE, json_record)
        logging.info(f"Record Created: {os.path.basename(path)}")
        return Player._TEMPLATE.copy()

    def save_record(self):
        tmp_path = f"{Player._RECORD_BASE_PATH}tmp_{self.user.id}.json"
        path = f"{Player._RECORD_BASE_PATH}{self.user.id}.json"

        with open(tmp_path, "w") as json_record:
            json.dump(self.record, json_record)

        os.remove(path)
        os.rename(tmp_path, path)
        logging.info(f"User {self.user}'s record has been saved")

    def add_games(self, games):
        self.record["games"] = list(set(games + self.record["games"]))
        self.save_record()
        logging.info(f'{", ".join(games)} successfully added to {self.user}\'s record.')

    def remove_games(self, games):
        for game in games:
            if game in self.record["games"]:
                self.record["games"].remove(game)

        self.save_record()
        logging.info(
            f'{", ".join(games)} successfully removed from {self.user}\'s record.'
        )

    def get_games(self):
        return self.record["games"]

    def add_blacklist_games(self, games):
        self.record["blacklist"] = list(set(games + self.record["blacklist"]))
        self.save_record()
        logging.info(f'{", ".join(games)} added to {self.user}\'s blacklist.')

    def remove_blacklist_games(self, games):
        for game in games:
            if game in self.record["blacklist"]:
                self.record["blacklist"].remove(game)
        self.save_record()
        logging.info(f'{", ".join(games)} removed from {self.user}\'s blacklist')

    def get_blacklist(self):
        return self.record["blacklist"]


class WhatShouldWePlayBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())

    async def on_ready(self):
        logging.info(f"Logged in as user {self.user.name}")

    async def on_message(self, message):
        if message.author == self.user:
            return

        tempCmd = message.content.split(" ", 1)
        if len(tempCmd) != 1:
            cmd, msg = tempCmd
        else:
            cmd = tempCmd[0]
            msg = "NONE"
        cmd = cmd.lower()

        if cmd not in [
            "$add",
            "$remove",
            "$list",
            "$blacklist",
            "$unblacklist",
            "$illuminate",
        ]:
            return

        logging.info(f"Message Received from {message.author}: {cmd} {msg}")

        author = message.author

        if cmd == "$add":
            games = [game.strip() for game in msg.split(",")]
            user = Player(author)
            user.add_games(games)
            await message.channel.send(
                f'{", ".join(games)} added to {author}\'s record'
            )
        elif cmd == "$remove":
            games = [game.strip() for game in msg.split(",")]
            user = Player(author)
            user.remove_games(games)
            await message.channel.send(
                f'{", ".join(games)} removed from {author}\'s record'
            )
        elif cmd == "$list":
            user = Player(author)
            msg = f'{", ".join(user.get_games())}'
            if msg == "":
                msg = "No games in library."
            await message.channel.send(msg)
        elif cmd == "$blacklist":
            games = [game.strip() for game in msg.split(",")]
            user = Player(author)
            user.add_blacklist_games(games)
            await message.channel.send(
                f'{", ".join(games)} added to {author}\'s blacklist'
            )
        elif cmd == "$unblacklist":
            games = [game.strip() for game in msg.split(",")]
            user = Player(author)
            user.remove_blacklist_games(games)
            await message.channel.send(
                f'{", ".join(games)} removed from {author}\'s blacklist'
            )
        elif cmd == "$illuminate":
            user = Player(author)
            msg = f'{", ".join(user.get_blacklist())}'
            if msg == "":
                msg = "No games in blacklist."
            await message.channel.send(msg)
        return

    async def on_member_update(self, prev, cur):
        if prev.activities == cur.activities:
            return

        user = Player(cur)
        if not hasattr(cur.activity, "type"):
            return

        if cur.activity.type is discord.ActivityType.playing:
            user.add_games([cur.activity.name])
            logging.info(
                f"User starting playing {cur.activity.name}. Added to gamelist"
            )


if __name__ == "__main__":
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.ERROR)
    stream_handler.addFilter(Filter(logging.ERROR))
    file_handler = logging.FileHandler(f"{date.today()}.log")

    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        level=logging.INFO,
        handlers=[stream_handler, file_handler],
    )

    client = WhatShouldWePlayBot()
    client.run(os.getenv("TOKEN"))
