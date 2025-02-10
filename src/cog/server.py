# A discord bot cog that manages server metadata
from typing import List, Optional, Set
import discord
from discord.ext import commands
from orm import db_session, Game, Player
from pony.orm import select, coalesce
from cog.converter import GamePlayerCount
import random


class ServerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def suggest(self, ctx: commands.Context, filter: Optional[str] = None):
        """Suggest a game to play"""
        if not ctx.guild:
            await ctx.send("This command is only available in servers.")
            return
        all_games = self.get_games_guild(ctx.guild)
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
        games = self.suggest_game(ctx.guild, all_games, member_count)
        if games:
            await ctx.send(", ".join(games))
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
    def get_games_guild(self, guild: discord.Guild) -> List[Set[str]]:
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

        games = set.intersection(*game_data)
        bans = self.get_guild_bans(guild)

        # Filters the games to only those that meet the following criteria:
        # 1. The game in the table is in the list of possible games
        # 2. The player count is greater than or equal to the player count requested
        # 3. The game is not in the ban list (or the bot is ignoring the ban list)
        with db_session:
            subquery = select(g for g in Game).filter(
                lambda g: g.name in games
                and coalesce(g.player_count, player_count) >= player_count
                and (g.name not in bans or self.bot._ignore_banlist)
            )

            games = list(select(g.name for g in subquery)[:])

        # This is checking to see if there are any games in the list because
        # random.choice breaks if you give it an empty list.
        suggest_count = 5
        if not games:
            return None
        else:
            if len(games) > suggest_count:
                return random.sample(games, suggest_count)
            else:
                return games

    @db_session
    def get_guild_bans(self, guild: discord.Guild) -> List[str]:
        disallowlist = []
        for member in guild.members:
            if member.id not in self.bot._MEMBER_IGNORE_LIST and member.status == discord.Status.online:
                player = Player.get(id=str(member.id)) or Player(id=str(member.id), name=member.name)
                disallowlist += [game.name for game in player.get_banned_games()]
        return disallowlist
