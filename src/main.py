import discord
import os
import sys
import logging
import random
from datetime import date
from dotenv import load_dotenv
from orm import Player, Game, SteamMetaData, init_database
from pony.orm import db_session
from steamapi import SteamAPI

load_dotenv()


class Filter(object):
    def __init__(self, level):
        self.__level = level

    def filter(self, logRecord):
        return logRecord.levelno <= self.__level


class WhatShouldWePlayBot(discord.Client):
    # These are the member id's for the bots, we ignore them for specific checks
    _MEMBER_IGNORE_LIST = [959263650701508638, 961433803484712960]
    _ignore_disallowlist = False
    _member_count = -1
    api = SteamAPI(os.getenv("API_KEY"))

    def __init__(self, db_path: str = ":memory:"):
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

        init_database(db_path, self.api.get_app_list())

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
        id = str(author.id)

        match cmd:
            case "$add":
                if msg == "NONE":
                    await message.channel.send(
                        "No game provided. Please add games using '$add Game1, Game2'"
                    )
                games = [game.strip() for game in msg.split(",")]

                with db_session:
                    user = Player.get(id=id) or Player(id=id, name=author.name)
                    user.add_games(*games)

                await message.channel.send(
                    f'{", ".join(games)} added to {author}\'s record'
                )
            case "$remove":
                games = [game.strip() for game in msg.split(",")]

                with db_session:
                    user = Player.get(id=id) or Player(id=id, name=author.name)
                    user.remove_games(*games)

                await message.channel.send(
                    f'{", ".join(games)} removed from {author}\'s record'
                )
            case "$list":
                out_msg = ""
                if msg == "NONE":
                    msg = "games bans"
                with db_session:
                    user = Player.get(id=id) or Player(id=id, name=author.name)
                    names = [game.name for game in user.get_games()]
                    bans = [game.name for game in user.get_banned_games()]
                if "games" in msg:
                    out_msg += f"Games: {', '.join(names)}\n"
                if "bans" in msg:
                    out_msg += f"Banned Games: {', '.join(bans)}"
                await message.channel.send(out_msg)
            case "$ban":
                games = [game.strip() for game in msg.split(",")]

                with db_session:
                    user = Player.get(id=id) or Player(id=id, name=author.name)
                    user.add_banned_games(*games)

                await message.channel.send(
                    f'{", ".join(games)} added to {author}\'s disallowlist'
                )
            case "$unban":
                games = [game.strip() for game in msg.split(",")]

                with db_session:
                    user = Player.get(id=id) or Player(id=id, name=author.name)
                    user.remove_banned_games(*games)

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

                    with db_session:
                        game = Game.get(name=game) or Game(name=game)
                        game.set_player_count(int(count))

                    out_msg = f'"Set max player count of {game.name} to {count}"'
                else:
                    out_msg = "Incorrect command set player count using '$set <game> <max_player_count>'"
                await message.channel.send(out_msg)
            case "$link":
                steamid = msg.strip()
                games_data = self.api.get_games(steamid)
                if not games_data:
                    await message.channel.send("Invalid Steam ID or private profile.")
                    return
                appids = []
                with db_session:
                    for game_data in games_data:
                        steam_metadata = SteamMetaData.get(appid=game_data["appid"])
                        if not steam_metadata:
                            game_info = self.api.get_games_by_id(game_data["appid"])
                            if not game_info:
                                continue
                            name = game_info["name"]
                            if not name:
                                continue
                            SteamMetaData(
                                appid=game_data["appid"],
                                name=name,
                                game=Game(name=name),
                            )
                        appids.append(game_data["appid"])

                with db_session:
                    user = Player.get(id=id) or Player(id=id, name=author.name)
                    user.add_games_with_appid(*appids)

                await message.channel.send(f"{len(appids)} added to {author}'s record")
        return

    async def on_presence_update(self, prev, cur):
        if prev.activities == cur.activities:
            return

        if not hasattr(cur.activity, "type"):
            return

        with db_session:
            user = Player.get(id=str(cur.id)) or Player(id=str(cur.id), name=cur.name)
            if cur.activity.type is discord.ActivityType.playing:
                user.add_games(cur.activity.name)
                logging.info(
                    f"User starting playing {cur.activity.name}. Added to user gamelist"
                )

    @db_session
    def get_player_count(self, games):
        data = {}
        for game in games:
            game = Game.get(name=game) or Game(name=game)
            data[game.name] = game.player_count or self._member_count
        return data

    @db_session
    def get_games_guild(self, guild):
        game_data = []
        for member in guild.members:
            if (
                member.id not in self._MEMBER_IGNORE_LIST
                and member.status == discord.Status.online
            ):
                player = Player.get(id=str(member.id)) or Player(
                    id=str(member.id), name=member.name
                )
                game_data.append([game.name for game in player.get_games()])
        return game_data

    @db_session
    def get_guild_ban_list(self, guild):
        disallowlist = []
        for member in guild.members:
            if (
                member.id not in self._MEMBER_IGNORE_LIST
                and member.status == discord.Status.online
            ):
                player = Player.get(id=str(member.id)) or Player(
                    id=str(member.id), name=member.name
                )
                disallowlist += [game.name for game in player.get_banned_games()]
        return disallowlist

    def suggest_game_for_channel(self, channel, player_data):
        game = self.suggest_game(channel.guild, player_data, len(channel.members))
        return game

    def suggest_game(self, guild, game_data, player_count):
        potential_games = []
        for gamelist in game_data:
            potential_games.append(set(gamelist))

        potential_games = set.intersection(*potential_games)
        player_counts = self.get_player_count(potential_games)
        disallowlist = self.get_guild_ban_list(guild)
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
    client = WhatShouldWePlayBot(os.getenv("DB_PATH"))
    client.run(os.getenv("TOKEN"))
