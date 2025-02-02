import pytest_asyncio
import pytest
from main import WhatShouldWePlayBot, Player, Game, db_session
from discord.ext import test
import os
import discord


@pytest_asyncio.fixture
async def bot():
    bot = WhatShouldWePlayBot()
    await bot._async_setup_hook()

    test.configure(bot)

    yield bot

    await test.empty_queue()


@pytest.fixture
def user():
    user = discord.User
    user.id = os.getenv("ID")


@pytest.mark.asyncio
async def test_add_games(bot):
    member = await test.member_join()
    id = str(member.id)
    # Adding games
    await test.message("$Add Game1, Game 2", member=member)
    with db_session:
        player = Player.get(id=id)
        games = [game.name for game in player.get_games()]
        assert sorted(games) == sorted(["Game 2", "Game1"])

    # Adding to ban list
    await test.message("$ban Game 2", member=member)
    with db_session:
        player = Player.get(id=id)
        games = [game.name for game in player.get_banned_games()]
        assert sorted(games) == sorted(["Game 2"])

    # Checking that suggest * works
    await test.message("$suggest *", member=member) is not None

    # Checking setting a player works
    await test.message("$set Game 1, 3", member=member)
    with db_session:
        game = Game.get(name="Game 1")
        assert game.get_player_count() == 3

    # Checking numerical suggestion works
    assert await test.message("$suggest 2", member=member) is not None

    # Checking for voice channel suggestions
    assert await test.message("$suggest General", member=member) is not None

    # Check that removing from disallowlist works
    await test.message("$unban Game 2", member=member)
    with db_session:
        player = Player.get(id=id)
        games = [game.name for game in player.get_banned_games()]
        assert games == []

    # Remove a game and test
    await test.message("$remove Game1", member=member)
    with db_session:
        player = Player.get(id=id)
        games = [game.name for game in player.get_games()]
        assert games == ["Game 2"]

    # Make sure list works with games populated
    assert await test.message("$list", member=member) is not None

    # Remove the last game and make sure it's empty
    await test.message("$remove Game 2", member=member)
    with db_session:
        player = Player.get(id=id)
        games = [game.name for game in player.get_games()]
        assert games == []

    # Make sure the list doesn't fail when there are no games
    assert await test.message("$list", member=member) is not None


@pytest.mark.asyncio
async def test_from_player(bot):
    member = await test.member_join()
    with db_session:
        player = Player(id=str(member.id), name=member.name)

        # Adding games
        player.add_games("Game1", "Game 2")
        assert sorted([game.name for game in player.get_games()]) == sorted(
            ["Game 2", "Game1"]
        )

        # Remove a games and test
        player.remove_games("Game1")
        assert sorted([game.name for game in player.get_games()]) == ["Game 2"]

        player.remove_games("Game 2")
        assert [game.name for game in player.get_games()] == []

        # Adding games to disallow list
        player.add_banned_games("Game1", "Game 2")
        assert sorted([game.name for game in player.get_banned_games()]) == sorted(
            ["Game 2", "Game1"]
        )

        # Remove a games and test
        player.remove_banned_games("Game1")
        assert sorted([game.name for game in player.get_banned_games()]) == ["Game 2"]

        player.remove_banned_games("Game 2")
        assert [game.name for game in player.get_banned_games()] == []
