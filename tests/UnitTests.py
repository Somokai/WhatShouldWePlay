import unittest
from discordwebhook import Discord
import time
import json
from dotenv import load_dotenv
import os
from main import Player
import discord

load_dotenv()
TEST_FILE_PLAYER = f"Players\{os.getenv('ID')}.json"
TEST_FILE_GAMELIST = "GameList.json"

def get_data():
    with open(TEST_FILE_PLAYER, 'r') as jsonFile:
        games = json.load(jsonFile)
        return games

def get_gamelist():
        with open(TEST_FILE_GAMELIST, 'r') as jsonFile:
            games = json.load(jsonFile)
            return games

class TestCommands(unittest.TestCase):

    def test_from_discord(self):
        # Adding games
        discord.post(content = "$Add Game1, Game 2")
        time.sleep(1)
        games = get_data()
        self.assertEqual(sorted(games['games']), sorted(['Game 2','Game1']))  

        # Adding to disallowlist and checking for suggestions
        discord.post(content = "$disallowlist Game 2")
        time.sleep(1)
        games = get_data()
        self.assertEqual(games['disallowlist'], ['Game 2'])

        # Checking that suggest * works
        discord.post(content = "$suggest *")

        # Just setting a player count to make sure the functionality works
        discord.post(content = "$set Game 1, 3")
        time.sleep(1)
        game_data = get_gamelist()
        self.assertEqual(game_data['Game 1'], '3')

        # Making sure suggestion doesn't fail
        discord.post(content = "$suggest 2")

        # Checking for voice channel suggestions
        discord.post(content = "$suggest General")

        # Adding to disallowlist and checking for suggestions, should contain help message
        discord.post(content = "$undisallowlist Game 2")
        time.sleep(1)
        games = get_data()
        self.assertEqual(games['disallowlist'], [])

        # Remove a game and test
        discord.post(content = "$remove Game1")
        time.sleep(1)
        games = get_data()
        self.assertEqual(games['games'], ['Game 2'])

        # Make sure list works with games populated
        discord.post(content = "$list")
        
        # Remove the last game and make sure it's empty
        discord.post(content = "$REMOVE Game 2")
        time.sleep(1)
        games = get_data()
        self.assertEqual(games['games'], [])   

        # Make sure the list doesn't fail when there are no games
        discord.post(content = "$list")

    def test_from_player(self):
        # Adding games
        player.add_games(['Game1', 'Game 2'])
        games = get_data()
        print(games)
        self.assertEqual(sorted(games['games']), ['Game 2','Game1'])

        # Remove a games and test
        player.remove_games(['Game1'])
        games = get_data()
        self.assertEqual(games['games'], ['Game 2'])

        player.remove_games(['Game 2'])
        games = get_data()
        self.assertEqual(games['games'], [])   

        # Make sure the get_data method works
        games = get_data()
        player_games = player.get_games()
        self.assertEqual(sorted(games['games']), sorted(player_games)) 

        # Adding games
        player.add_disallowlist_games(['Game1', 'Game 2'])
        games = get_data()
        print(games)
        self.assertEqual(sorted(games['disallowlist']), sorted(['Game1','Game 2']))

        # Make sure disallow works in get_data
        player_disallow = player.get_disallowlist()   
        self.assertEqual(sorted(games['disallowlist']), sorted(player_disallow))

        # Remove a games and test
        player.remove_disallowlist_games(['Game1'])
        games = get_data()
        self.assertEqual(games['disallowlist'], ['Game 2'])

        player.remove_disallowlist_games(['Game 2'])
        games = get_data()
        self.assertEqual(games['disallowlist'], [])   

        # Make sure the get_data method works
        games = get_data()
        player_games = player.get_games()
        self.assertEqual(sorted(games['games']), sorted(player_games))   

if __name__ == '__main__':
    if os.path.exists(TEST_FILE_PLAYER):
        os.remove(TEST_FILE_PLAYER)

    user = discord.User
    user.id = os.getenv('ID')
    discord = Discord(url = os.getenv('URL'))
    player = Player(user)    
    unittest.main()
    
    