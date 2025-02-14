import discord
from discord.ui import View, Button, Modal, TextInput, Select, button, select


class _JumpToPageModal(Modal):
    def __init__(self, parent: "GameView"):
        super().__init__(title="Jump to Page", timeout=30.0)
        self.parent = parent
        self.page_input = TextInput(label="Enter a page number", placeholder=1, required=True)
        self.add_item(self.page_input)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent.user_id:
            await self.parent.update_message(interaction, self.parent.current_page)

        try:
            page_number = min(
                int(self.page_input.value),
                self.parent.max_ban_page if self.parent.view_bans else self.parent.max_game_page,
            )
        except ValueError:
            await self.parent.update_message(interaction, self.parent.current_page)

        await self.parent.update_message(interaction, page_number)


class GameView(View):
    def __init__(self, user_id: int, games: list[str], bans: list[str], view_bans: bool = False):
        super().__init__()
        self.user_id = user_id
        self.current_page = 1
        self.max_ban_page = len(bans) // 10
        self.max_game_page = len(games) // 10
        self.games = GameView.pad_str(games)
        self.bans = GameView.pad_str(bans)
        self.view_bans = view_bans
        self.update_page_lock()

    def get_chunk(arr: list[any], index: int, chunk_size: int = 10):
        start = index * chunk_size
        end = start + chunk_size
        chunk = arr[start:end]
        while len(chunk) < chunk_size:
            chunk.append(" " * 40)

        return chunk

    def pad_str(strings: list[str]):
        if not strings:
            return []
        max_len = 50
        trim = max_len - 3

        for i in range(len(strings)):
            if len(strings[i]) > max_len:
                strings[i] = f"{strings[i][:trim]}..."
            if len(strings[i]) < max_len:
                strings[i] = f"{strings[i].ljust(max_len)}"

        return strings

    def embed(self) -> discord.Embed:
        embed = discord.Embed(title="Your Games Registered with me!")

        if self.view_bans:
            games = self.bans
            name = "Your Banned Games"
        else:
            games = self.games
            name = "Your Games"

        games = "\n".join(GameView.get_chunk(games, self.current_page))
        games = f"```\n{games}```"

        embed.add_field(name=name, value=games, inline=True)
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

    @button(label="⬅️ Previous", style=discord.ButtonStyle.primary)
    async def previous_page(self, interaction: discord.Interaction, _button: Button):
        if interaction.user.id != self.user_id:
            await self.update_message(interaction, self.current_page)
            return

        if self.current_page > 1:
            await self.update_message(interaction, self.current_page - 1)

    @button(label="Jump To", style=discord.ButtonStyle.secondary)
    async def jump_to_page(self, interaction: discord.Interaction, _button: Button):
        if interaction.user.id != self.user_id:
            await self.update_message(interaction, self.current_page)
            return

        await interaction.response.send_modal(_JumpToPageModal(self))

    @select(
        placeholder="Game Type",
        options=[
            discord.SelectOption(label="Games", value="games"),
            discord.SelectOption(label="Banned Games", value="banned"),
        ],
    )
    async def select(self, interaction: discord.Interaction, select: Select):
        old = self.view_bans
        self.view_bans = select.values[0] == "banned"
        if old == self.view_bans:
            await self.update_message(interaction, self.current_page)
        else:
            await self.update_message(interaction, 1)

    @button(label="Next ➡️", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, _button: Button):
        if interaction.user.id != self.user_id:
            await self.update_message(interaction, self.current_page)
            return

        await self.update_message(interaction, self.current_page + 1)


class WhichGame(View):
    def __init__(self, user_id: int, user_input: str, *games: list[str]):
        super().__init__()
        self.games = games
        self.user_input = user_input
        self.user_id = user_id
        self.selection = None
        self.add_item(Dropdown(user_id, user_input, games))

    def embed(self) -> discord.Embed:
        embed = discord.Embed(title="We couldn't find an exact match.\nDid you mean one of these?")
        embed.add_field(name="Your Input", value=f"```\n{self.user_input}```", inline=False)
        return embed


class Dropdown(discord.ui.Select):
    def __init__(self, user_id: int, user_input: str, games: list[str]):
        self.user_id = user_id
        self.user_input = user_input
        options = []
        for game in games:
            options.append(discord.SelectOption(label=game, description="This One!"))
        options.append(
            discord.SelectOption(
                label="None of These",
                description="Not seeing your game? Try again, but be more specific.",
                value="none",
            )
        )
        options.append(
            discord.SelectOption(label="Add Game", description="Not seeing your game? Add it anyway.", value="add")
        )
        super().__init__(placeholder="Choose Game", options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("No touch!", ephemeral=True)
            return
        selection = self.values[0]
        match selection:
            case "none":
                await interaction.response.send_message("We couldn't find this game. Try again.", ephemeral=True)
            case "add":
                self.view.selection = self.user_input
                await interaction.response.send_message(f"Alright I'll add {self.user_input}", ephemeral=True)
            case _:
                self.view.selection = selection
                await interaction.response.send_message(f"You selected {self.view.selection}.", ephemeral=True)
        self.disabled = True
        self.placeholder = self.view.selection
        await interaction.message.edit(view=self.view)
        self.view.stop()
