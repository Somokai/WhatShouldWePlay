# A module for any custom argument converters for commands

from discord.ext import commands

# Parses commands like `Game 1 players: 3`
class GamePlayerCount(commands.FlagConverter, delimiter=':', case_insensitive=True):
    game: str = commands.flag(positional=True)
    players: int
