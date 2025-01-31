import pytest_asyncio
import pytest
from main import WhatShouldWePlayBot, Player
from discord.ext import test
import os
import json
import discord

TEST_FILE_GAMELIST = "GameList.json"

def get_data(member):
    with open(f"Players/{member.id}.json", "r") as jsonFile:
        games = json.load(jsonFile)
        return games

def get_gamelist():
    if not os.path.isfile("GameList.json"):
        with open("GameList.json", "w") as json_record:
            json.dump({}, json_record)
    with open(TEST_FILE_GAMELIST, "r") as jsonFile:
        games = json.load(jsonFile)
        return games

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

    # Adding games
    await test.message("$Add Game1, Game 2", member=member)
    games = get_data(member)
    assert sorted(games["games"]) == sorted(["Game 2", "Game1"])

    # Adding to disallowlist
    await test.message("$disallowlist Game 2", member=member)
    games = get_data(member)
    assert games["disallowlist"] == ["Game 2"]

    # Checking that suggest * works
    await test.message("$suggest *", member=member) is not None

    # Checking setting a player works
    await test.message("$set Game 1, 3", member=member)
    game_data = get_gamelist()
    assert game_data["Game 1"] == "3"

    # Checking numerical suggestion works
    assert await test.message("$suggest 2", member=member) is not None

    # Checking for voice channel suggestions
    assert await test.message("$suggest General", member=member) is not None

    # Adding to disallowlist and checking for suggestions
    await test.message("$undisallowlist Game 2", member=member)
    games = get_data(member)
    assert games["disallowlist"] == []

    # Remove a game and test
    await test.message("$remove Game1", member=member)
    games = get_data(member)
    assert games["games"] == ["Game 2"]

    # Make sure list works with games populated
    assert await test.message("$list", member=member) is not None

    # Remove the last game and make sure it's empty
    await test.message("$remove Game 2", member=member)
    games = get_data(member)
    assert games["games"] == []

    # Make sure the list doesn't fail when there are no games
    assert await test.message("$list", member=member) is not None

@pytest.mark.asyncio
async def test_from_player():
    member = await test.member_join()
    player = Player(member)

    # Adding games
    player.add_games(["Game1", "Game 2"])
    games = get_data(member)
    assert sorted(games["games"]) == sorted(["Game 2", "Game1"])

    # Remove a games and test
    player.remove_games(["Game1"])
    games = get_data(member)
    assert games["games"] == ["Game 2"]

    player.remove_games(["Game 2"])
    games = get_data(member)
    assert games["games"] == []

    # Make sure the get_data method works
    games = get_data(member)
    player_games = player.get_games()
    assert sorted(games["games"]) == sorted(player_games)

    # Adding games to disallow list
    player.add_disallowlist_games(["Game1", "Game 2"])
    games = get_data(member)
    assert sorted(games["disallowlist"]) == sorted(["Game 2", "Game1"])

    # Make sure disallow works in get_data
    player_disallow = player.get_disallowlist()
    assert sorted(games["disallowlist"]) == sorted(player_disallow)

    # Remove a games and test
    player.remove_disallowlist_games(["Game1"])
    games = get_data(member)
    assert sorted(games["disallowlist"]) == sorted(["Game 2"])

    player.remove_disallowlist_games(["Game 2"])
    games = get_data(member)
    assert games["disallowlist"] == []

    # Make sure the get_data method works
    games = get_data(member)
    player_disallow = player.get_disallowlist()
    assert sorted(games["disallowlist"]) == sorted(player_disallow)
