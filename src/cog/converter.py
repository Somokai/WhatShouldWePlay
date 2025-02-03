# A module for any custom argument converters for commands

from discord.ext import commands


# Parses commands like `Game 1 players: 3`
class GamePlayerCount(commands.FlagConverter, delimiter=":", case_insensitive=True):
    game: str = commands.flag(positional=True)
    players: int


# parses a list of games separated by commas
class GameList(commands.Converter):
    async def convert(self, _ctx: commands.Context, argument: str) -> list[str]:
        return [game.strip() for game in argument.split(",")]
