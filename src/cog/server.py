# A discord bot cog that manages server metadata
from typing import List, Optional, Set
import discord
from discord.ext import commands
from orm import db_session, Game, Player
from cog.converter import GamePlayerCount
import random


class ServerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def suggest(self, ctx: commands.Context, filter: Optional[str] = None):
        """Suggest a game to play"""
        member_count = len(ctx.guild.members)
        all_games = self.get_games_guild(ctx.guild)
        member_count = 0
        if filter is None or filter == "*":
            member_count = len(ctx.guild.members)
        elif filter.isdigit():
            member_count = int(filter)
        else:
            for channel in ctx.guild.voice_channels:
                if filter == channel.name:
                    member_count = len(channel.members)
            else:
                await ctx.send("Selected channel is not a voice channel or spelled incorrectly. Try again.")
                return
        game = self.suggest_game(ctx.guild, all_games, member_count)
        if game:
            await ctx.send(game)
        else:
            await ctx.send(f"No Compatible games for player count of {member_count}")

    @commands.group(name="admin", invoke_without_command=True)
    # @commands.has_permissions(administrator=True) # TODO Add permission check
    async def admin(self, ctx: commands.Context):
        """Admin commands for the bot"""
        await ctx.send_help(ctx.command)

    @admin.command()
    # @commands.has_permissions(administrator=True) # TODO: Add permission check
    async def set(self, ctx: commands.Context, *, config: GamePlayerCount):
        """Set the player count for a game"""
        name = config.game
        players = config.players
        with db_session:
            game = Game.get(name=name) or Game(name=name)  # TODO: Limit to guild managed games
            if game is None:
                await ctx.message.add_reaction("👎")
                await ctx.send("Game not found.")
                return

            game.set_player_count(players)
        await ctx.message.add_reaction("👍")

    @admin.command()
    # @commands.has_permissions(administrator=True) # TODO: Add permission check
    async def list(self, ctx: commands.Context):
        """List all games"""
        with db_session:
            games = Game.select()  # TODO Limit to guild managed games
            games = [game.name for game in games]
        await ctx.send(f"Games: {', '.join(games)}")

    @admin.command()
    # @commands.has_permissions(administrator=True) # TODO: Add permission check
    async def ignore_bans(self, ctx: commands.Context, ignore: bool):
        """Ignore user bands when selecting games."""
        # TODO: Add this to a server settings table and keep this restriction to
        # individual servers.
        self.bot._ignore_banlist = ignore
        await ctx.message.add_reaction("👍")

    @db_session
    def get_games_guild(self, guild) -> List[Set[str]]:
        """Returns a list, where each element is a set of games that a user in the guild has."""
        game_data = []
        for member in guild.members:
            if member.id not in self.bot._MEMBER_IGNORE_LIST and member.status == discord.Status.online:
                player = Player.get(id=str(member.id)) or Player(id=str(member.id), name=member.name)
                game_data.append(set([game.name for game in player.get_games()]))
        return game_data

    def suggest_game(self, guild: discord.Guild, game_data: List[Set[str]], player_count: int) -> Optional[str]:
        if not game_data:
            return None
        potential_games = set.intersection(*game_data)
        player_counts = self.get_game_player_counts(*potential_games, default=player_count)
        banlist = self.get_guild_bans(guild)
        games = []
        for game in potential_games:
            count_ok = player_counts[game] >= int(player_count)
            banlist_ok = game not in banlist or self.bot._ignore_banlist
            if count_ok and banlist_ok:
                games.append(game)

        # This is checking to see if there are any games in the list because
        # random.choice breaks if you give it an empty list.
        # Note: this is the correct way to check for an empty list apparently.
        if not games:
            return None
        else:
            return random.choice(games)

    @db_session
    def get_game_player_counts(self, *games: str, default=0) -> dict[str, int]:
        """Returns a dictionary of game names to player counts."""
        data = {}
        for game in games:
            game = Game.get(name=game) or Game(name=game)
            data[game.name] = game.player_count or default
        return data

    @db_session
    def get_guild_bans(self, guild: discord.Guild) -> List[str]:
        disallowlist = []
        for member in guild.members:
            if member.id not in self.bot._MEMBER_IGNORE_LIST and member.status == discord.Status.online:
                player = Player.get(id=str(member.id)) or Player(id=str(member.id), name=member.name)
                disallowlist += [game.name for game in player.get_banned_games()]
        return disallowlist
