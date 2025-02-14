# A discord bot cog that manages user metadata
from discord.ui import View, Button
import discord
from discord.ext import commands
from pony.orm import db_session
from orm import Player, Game, SteamMetaData
import logging
from .converter import GameList
from .ui import GameView, WhichGame


class UserCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def match_game(self, ctx: commands.Context, name: str) -> str:
        # This function is contained in here to keep context the same and because it's not used elsewhere
        async def get_selection(ctx: commands.Context, name: str, *possible_names: list[str]):
            possible_names = set(possible_names)
            # Dropdowns have a max length of 25
            if len(possible_names) > 25:
                await ctx.send(f"Too many games similar to {name}, please be more specific.", ephemeral=True)
                return
            view = WhichGame(ctx.author.id, name, *possible_names)
            await ctx.send(embed=view.embed(), view=view, ephemeral=True)
            await view.wait()
            if view.selection:
                return view.selection

        # Clean up the string a bit before we search the tables
        name = name.strip()

        # 1. Check if the name exists in the database. Note: we can have name dupes in the database,
        # so we will just use this name and fall back on the None SteamMetaData in calling method.
        with db_session:
            # TODO: switch to MetaData
            games = Game.select(name=name)[:] or SteamMetaData.select(name=name)[:]
            if games:
                return games[0].name

        # 2. Check if the name exists in the database with a different case
        with db_session:
            games = (
                Game.select(lambda g: g.name.lower() == name.lower())[:]
                # TODO: switch to MetaData
                or SteamMetaData.select(lambda g: g.name.lower() == name.lower())[:]
            )
            if games:
                possible_names = [game.name for game in games]
                name = await get_selection(ctx, name, *possible_names)
                # This will return None if no games are selected
                return name

        # 3. If not, check if the name exists with a different case or in partial form
        with db_session:
            if games:
                games = list(Game.select(lambda g: g.name.lower().startswith(name.lower()))[:])
                games.extend(Game.select(lambda g: g.name.lower().endswith(name.lower()))[:])
            else:
                # TODO: switch to MetaData
                games = list(SteamMetaData.select(lambda g: g.name.lower().startswith(name.lower()))[:])
                games.extend(SteamMetaData.select(lambda g: g.name.lower().endswith(name.lower()))[:])
            if games:
                possible_names = [game.name for game in games]
                name = await get_selection(ctx, name, *possible_names)
                # This will return None if no games are selected
                return name

        # 4. If we don't find a match, we just add the game
        return name

    async def match_games(self, ctx: commands.Context, *names: list[str]) -> list[str]:
        cleaned_names = []

        for name in names:
            name = await self.match_game(ctx, name)
            if name:
                cleaned_names.append(name)

        return cleaned_names

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
        games = await self.match_games(ctx, *games)
        # If no games were selected, don't add anything
        if not games:
            return

        id = str(ctx.author.id)
        with db_session:
            player = Player.get(id=id) or Player(id=id, name=ctx.author.name)
            player.add_games(*games)

        logging.info(f"Added {games} to {ctx.author.name}")
        await ctx.message.add_reaction("👍")

    @commands.command()
    async def remove(self, ctx: commands.Context, *, games: GameList):
        """Remove games from user profile"""
        games = await self.match_games(ctx, *games)
        # If no games were selected, don't remove anything
        if not games:
            return

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
        games = await self.match_games(ctx, *games)
        # If no games were selected, don't ban anything
        if not games:
            return

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
        games = await self.match_games(ctx, *games)
        # If no games were selected, don't unban anything
        if not games:
            return

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
                # Note: I am not using the match_games method here because I don't want to get the user involved.
                game = cur.activity.name.strip()
                user.add_games(game)
                logging.info(f"User starting playing {cur.activity.name}. Added to user gamelist")
