# A discord bot cog that manages user metadata
from discord.ui import View, Button
import discord
from discord.ext import commands
from pony.orm import db_session
from orm import Player, Game, SteamMetaData
from .converter import GameList
import logging


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
            
            view = PaginationView(interaction.user.id, games, bans, view_bans=view_bans)
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

        #view = PaginationView(ctx.author.id, games, bans)
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


class JumpToPageModal(discord.ui.Modal):
    def __init__(self, parent: 'PaginationView'):
        super().__init__(title="Jump to Page", timeout=30.0)
        self.parent = parent
        self.page_input = discord.ui.TextInput(label="Enter a page number", placeholder=1, required=True)
        self.add_item(self.page_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent.user_id:
            await self.parent.update_message(interaction, self.parent.current_page)
        
        try:
            page_number = min(int(self.page_input.value), self.parent.max_ban_page if self.parent.view_bans else self.parent.max_game_page)
        except ValueError:
            await self.parent.update_message(interaction, self.parent.current_page)
        
        await self.parent.update_message(interaction, page_number)
        
class PaginationView(View):
    def __init__(self, user_id: int, games: list[str], bans: list[str], view_bans: bool=False):

        super().__init__()
        self.user_id = user_id
        self.current_page = 1
        self.max_ban_page = len(bans) // 10
        self.max_game_page = len(games) // 10
        self.games = PaginationView.pad_str(games)
        self.bans = PaginationView.pad_str(bans)
        self.view_bans = view_bans
        self.update_page_lock()
    
    def get_chunk(arr: list[any], index: int, chunk_size: int=10):
        start = index * chunk_size
        end = start + chunk_size 
        chunk = arr[start:end]
        while len(chunk) < chunk_size:
            chunk.append(" "*40)

        return chunk

    def pad_str(strings: list[str]):
        if not strings:
            return []
        max_len = 50
        trim = max_len - 3

        for i in range(len(strings)):
            if len(strings[i]) > max_len:
                strings[i] = f'{strings[i][:trim]}...'
            if len(strings[i]) < max_len:
                strings[i] = f'{strings[i].ljust(max_len)}'
            
        return strings

    def embed(self) -> discord.Embed:
        embed = discord.Embed(title="Your Games Registered with me!")

        if self.view_bans:
            bans = PaginationView.get_chunk(self.bans, self.current_page)
            bans = "\n".join(PaginationView.get_chunk(self.bans, self.current_page))
            bans = f"```\n{bans}```"
            embed.add_field(name="Your Banned Games", value=bans, inline=True)
        else:
            games = PaginationView.get_chunk(self.games, self.current_page)
            games = "\n".join(PaginationView.get_chunk(self.games, self.current_page))
            games = f"```\n{games}```"
            embed.add_field(name="Your Games", value=games, inline=True)
        
        embed.set_footer(text=f"Page {self.current_page}")
        return embed
    
    def update_page_lock(self):
        self.previous_page.disabled = self.current_page == 1
        if self.view_bans:
            self.next_page.disabled = self.current_page >= self.max_ban_page
        else:
            self.next_page.disabled = self.current_page >= self.max_game_page

    async def update_message(self, interaction, page_number):
        self.current_page = page_number
        self.update_page_lock()
        await interaction.response.edit_message(embed=self.embed(), view=self)

    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.primary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await self.update_message(interaction, self.current_page)
            return

        if self.current_page > 1:
            await self.update_message(interaction, self.current_page - 1)

    @discord.ui.button(label="Jump To", style=discord.ButtonStyle.secondary)
    async def jump_to_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await self.update_message(interaction, self.current_page)
            return

        await interaction.response.send_modal(JumpToPageModal(self))
    
    @discord.ui.select(placeholder="Game Type", options=[discord.SelectOption(label="Games", value="games"),discord.SelectOption(label="Banned Games", value="banned")])
    async def select(self, interaction: discord.Interaction, select: discord.ui.Select):
        old = self.view_bans
        self.view_bans = select.values[0] == "banned"
        self.update_page_lock()
        if old == self.view_bans:
            await self.update_message(interaction, self.current_page)
        else:
            await self.update_message(interaction, 1)

    @discord.ui.button(label="Next ➡️", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await self.update_message(interaction, self.current_page)
            return

        await self.update_message(interaction, self.current_page + 1)
