# A discord bot cog that manages user metadata
from discord.ui import View, Button
import discord
from discord.ext import commands
from pony.orm import db_session
from orm import Player, Game, SteamMetaData
import logging
from .converter import GameList
from .ui import GameView


class UserCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def link(self, ctx: commands.Context, steam_id: str):
        """Register all games from your steam profile"""
        games_data = self.bot.api.get_games(steam_id)
        if not games_data:
            await ctx.send("Invalid Steam ID or private profile.")
            return
        appids = []
        with db_session:
            for game_data in games_data:
                steam_metadata = SteamMetaData.get(appid=game_data["appid"])
                if not steam_metadata:
                    game_info = self.bot.api.get_games_by_id(game_data["appid"])
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
            id = str(ctx.author.id)
            name = ctx.author.name
            user = Player.get(id=id) or Player(id=id, name=name)
            user.add_games_with_appid(*appids)

        await ctx.send(f"{len(appids)} added to {name}'s record")

    @commands.command()
    async def add(self, ctx: commands.Context, *, games: GameList):
        """Add games to user profile"""
        id = str(ctx.author.id)
        with db_session:
            player = Player.get(id=id) or Player(id=id, name=ctx.author.name)
            player.add_games(*games)

        logging.info(f"Added {games} to {ctx.author.name}")
        await ctx.message.add_reaction("👍")

    @commands.command()
    async def remove(self, ctx: commands.Context, *, games: GameList):
        """Remove games from user profile"""
        id = str(ctx.author.id)
        with db_session:
            player = Player.get(id=id)
            if player:
                player.remove_games(*games)

        logging.info(f"Removed {games} from {ctx.author.name}")
        await ctx.message.add_reaction("👍")

    @commands.command()
    async def ban(self, ctx: commands.Context, *, games: GameList):
        """Ban games from user profile"""
        id = str(ctx.author.id)
        with db_session:
            player = Player.get(id=id)
            if player:
                player.add_banned_games(*games)

        logging.info(f"Banned {games} from {ctx.author.name}")
        await ctx.message.add_reaction("👍")

    @commands.command()
    async def unban(self, ctx: commands.Context, *, games: GameList):
        """Unban games from user profile"""
        id = str(ctx.author.id)
        with db_session:
            player = Player.get(id=id)
            if player:
                player.remove_banned_games(*games)

        logging.info(f"Unbanned {games} from {ctx.author.name}")
        await ctx.message.add_reaction("👍")

    @commands.command()
    async def list(self, ctx: commands.Context):
        """List games in the user profile"""

        async def callback(interaction: discord.Interaction, view_bans: bool):
            with db_session:
                player = Player.get(id=str(interaction.user.id))
                games = sorted([games.name for games in player.get_games()])
                bans = sorted([games.name for games in player.get_banned_games()])

            view = GameView(interaction.user.id, games, bans, view_bans=view_bans)
            await interaction.response.send_message(embed=view.embed(), view=view, ephemeral=True)

        async def c1(interaction: discord.Interaction):
            await callback(interaction, False)

        async def c2(interaction: discord.Interaction):
            await callback(interaction, True)

        b1 = Button(label="Click to View Your Games")
        b1.callback = c1

        b2 = Button(label="Click to View Your Banned Games")
        b2.callback = c2

        view = View()
        view.add_item(b1)
        view.add_item(b2)

        # view = PaginationView(ctx.author.id, games, bans)
        await ctx.send(view=view)

    @commands.Cog.listener()
    async def on_presence_update(self, prev, cur):
        if prev.activities == cur.activities:
            return

        if not hasattr(cur.activity, "type"):
            return

        with db_session:
            user = Player.get(id=str(cur.id)) or Player(id=str(cur.id), name=cur.name)
            if cur.activity.type is discord.ActivityType.playing:
                user.add_games(cur.activity.name)
                logging.info(f"User starting playing {cur.activity.name}. Added to user gamelist")
