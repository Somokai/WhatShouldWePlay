import discord
import json
import os
import sys
import logging
import random
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
    _TEMPLATE = {"games": [], "disallowlist": []}

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
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a") as json_record:
            json.dump(Player._TEMPLATE, json_record)
        logging.info(f"Record Created: {os.path.basename(path)}")
        return Player._TEMPLATE.copy()

    def save_record(self):
        tmp_path = f"{Player._RECORD_BASE_PATH}tmp_{self.user.id}.json"
        path = f"{Player._RECORD_BASE_PATH}{self.user.id}.json"

        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(tmp_path, "w+") as json_record:
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

    def add_disallowlist_games(self, games):
        self.record["disallowlist"] = list(set(games + self.record["disallowlist"]))
        self.save_record()
        logging.info(f'{", ".join(games)} added to {self.user}\'s disallowlist.')

    def remove_disallowlist_games(self, games):
        for game in games:
            if game in self.record["disallowlist"]:
                self.record["disallowlist"].remove(game)
        self.save_record()
        logging.info(f'{", ".join(games)} removed from {self.user}\'s disallowlist')

    def get_disallowlist(self):
        return self.record["disallowlist"]


class WhatShouldWePlayBot(discord.Client):
    # These are the member id's for the bots, we ignore them for specific checks
    _MEMBER_IGNORE_LIST = [959263650701508638, 961433803484712960]
    _ignore_disallowlist = False
    _member_count = -1

    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(logging.INFO)
        stream_handler.addFilter(Filter(logging.INFO))
        file_handler = logging.FileHandler(f"{date.today()}.log")

        logging.basicConfig(
            format="%(asctime)s [%(levelname)s] %(message)s",
            level=logging.INFO,
            handlers=[stream_handler, file_handler],
        )

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

        logging.info(f"Message Received from {message.author}: {cmd} {msg}")

        author = message.author

        match cmd:
            case "$add":
                if msg == "NONE":
                    await message.channel.send(
                        "No game provided. Please add games using '$add Game1, Game2'"
                    )
                games = [game.strip() for game in msg.split(",")]
                user = Player(author)
                user.add_games(games)
                self.add_games_to_gamelist(games)
                await message.channel.send(
                    f'{", ".join(games)} added to {author}\'s record'
                )
            case "$remove":
                games = [game.strip() for game in msg.split(",")]
                user = Player(author)
                user.remove_games(games)
                await message.channel.send(
                    f'{", ".join(games)} removed from {author}\'s record'
                )
            case "$list":
                user = Player(author)
                out_msg = ", ".join(user.get_games())
                if out_msg == "":
                    out_msg = "No games in library."
                await message.channel.send(out_msg)
            case "$disallowlist":
                games = [game.strip() for game in msg.split(",")]
                user = Player(author)
                user.add_disallowlist_games(games)
                await message.channel.send(
                    f'{", ".join(games)} added to {author}\'s disallowlist'
                )
            case "$undisallowlist":
                games = [game.strip() for game in msg.split(",")]
                user = Player(author)
                user.remove_disallowlist_games(games)
                await message.channel.send(
                    f'{", ".join(games)} removed from {author}\'s disallowlist'
                )
            case "$suggest":
                self._member_count = len(message.guild.members)
                all_games = self.get_games_guild(message.guild)
                if msg == "*":
                    out_msg = self.suggest_game(
                        message.guild, all_games, self._member_count
                    )
                elif msg.isdigit():
                    out_msg = self.suggest_game(message.guild, all_games, int(msg))
                else:
                    out_msg = "Selected channel is not a voice channel or spelled incorrectly. Try again."
                    for channel in message.guild.channels:
                        if (
                            msg == channel.name
                            and channel.type == discord.ChannelType.voice
                        ):
                            out_msg = self.suggest_game_for_channel(channel, all_games)
                if out_msg == []:
                    out_msg = "No compatible games in library. Choose a different number of players, use '$suggest *', or set '$disallow false'."
                await message.channel.send(out_msg)
            case "$disallow":
                if msg == "true":
                    self._ignore_disallowlist = False
                    await message.channel.send("Use disallowlists set to True.")
                elif msg == "false":
                    self._ignore_disallowlist = True
                    await message.channel.send("Use disallowlists set to False.")
            case "$set":
                params = [input.strip() for input in msg.split(",")]
                if len(params) == 2:
                    game = params[0]
                    count = params[1]
                    self.set_player_count(game, count)
                    out_msg = f'"Set max player count of {game} to {count}"'
                else:
                    out_msg = "Incorrect command set player count using '$set <game> <max_player_count>'"
                await message.channel.send(out_msg)
        return

    async def on_presence_update(self, prev, cur):
        if prev.activities == cur.activities:
            return

        user = Player(cur)
        if not hasattr(cur.activity, "type"):
            return

        if cur.activity.type is discord.ActivityType.playing:
            user.add_games([cur.activity.name])
            logging.info(
                f"User starting playing {cur.activity.name}. Added to user gamelist"
            )
            self.add_games_to_gamelist([cur.activity.name])

    def add_games_to_gamelist(self, games):
        with open("GameList.json", "r") as json_record:
            data = json.load(json_record)

            if isinstance(games, str):
                games = [games]

            for game in games:
                if game not in data.keys():
                    data[game] = -1

        # Separate write to avoid appending
        with open("GameList.json", "w") as json_record:
            json.dump(data, json_record)

    def set_player_count(self, game, count):
        with open("GameList.json", "r") as json_record:
            data = json.load(json_record)
            if game in data.keys():
                oldCount = data[game]
                if oldCount == -1:
                    logging.info(f"Max player count for {game} set to {count}.")
                elif oldCount != count:
                    logging.info(
                        f"Max player count for {game} updated from {oldCount} to {count}."
                    )
            data[game] = count

        with open("GameList.json", "w") as json_record:
            json.dump(data, json_record)

    def get_player_count(self, games):
        with open("GameList.json", "r") as json_record:
            data = json.load(json_record)
            for game in games:
                if game not in data.keys():
                    data[game] = self._member_count
                else:
                    data[game] = int(data[game])
                    if data[game] == -1:
                        data[game] = self._member_count
        return data

    def get_games_guild(self, guild):
        game_data = []
        for member in guild.members:
            if (
                member.id not in self._MEMBER_IGNORE_LIST
                and member.status == discord.Status.online
            ):
                player = Player(member)
                game_data.append(player.get_games())
        return game_data

    def get_disallowlist_guild(self, guild):
        disallowlist = []
        for member in guild.members:
            if (
                member.id not in self._MEMBER_IGNORE_LIST
                and member.status == discord.Status.online
            ):
                player = Player(member)
                disallowlist += player.get_disallowlist()
        return disallowlist

    def suggest_game_for_channel(self, channel, player_data):
        game = self.suggest_game(channel.guild, player_data, len(channel.members))
        return game

    def suggest_game(self, guild, game_data, player_count):
        potential_games = []
        for gamelist in game_data:
            self.add_games_to_gamelist(gamelist)
            potential_games.append(set(gamelist))

        potential_games = set.intersection(*potential_games)
        player_counts = self.get_player_count(potential_games)
        disallowlist = self.get_disallowlist_guild(guild)
        games = []
        for game in potential_games:
            count_ok = player_count == "*" or player_counts[game] >= int(player_count)
            disallowlist_ok = game not in disallowlist or self._ignore_disallowlist
            if count_ok and disallowlist_ok:
                games.append(game)

        # This is checking to see if there are any games in the list because
        # random.choice breaks if you give it an empty list.
        # Note: this is the correct way to check for an empty list apparently.
        if not games:
            return games
        else:
            return random.choice(games)


if __name__ == "__main__":
    client = WhatShouldWePlayBot()
    client.run(os.getenv("TOKEN"))
