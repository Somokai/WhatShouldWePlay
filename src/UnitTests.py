import unittest
from discordwebhook import Discord
import time
import json
from dotenv import load_dotenv
import os
from main import Player
import discord

load_dotenv()
TEST_FILE = os.getenv('ID') + '.json'

def get_games():
    with open(TEST_FILE, 'r') as jsonFile:
        output = json.load(jsonFile)
        output['games'].sort()
        return output

class TestCommands(unittest.TestCase):

    def test_from_discord(self):
        # Adding games
        discord.post(content = "$Add Game1, Game 2")
        time.sleep(1)
        output = get_games()
        self.assertEqual(output['games'], ['Game 2','Game1'])  

        # Remove a game and test
        discord.post(content = "$remove Game1")
        time.sleep(1)
        output = get_games()
        self.assertEqual(output['games'], ['Game 2'])

        # Make sure list works with games populated
        discord.post(content = "$list")
        
        # Remove the last game and make sure it's empty
        discord.post(content = "$REMOVE Game 2")
        time.sleep(1)
        output = get_games()
        self.assertEqual(output['games'], [])   

        # Make sure the list doesn't fail when there are no games
        discord.post(content = "$list")

    def test_from_player(self):
        # Adding games
        player.add_games(['Game1', 'Game 2'])
        output = get_games()
        print(output)
        self.assertEqual(output['games'], ['Game 2','Game1'])

        # Remove a games and test
        player.remove_games(['Game1'])
        output = get_games()
        self.assertEqual(output['games'], ['Game 2'])

        player.remove_games(['Game 2'])
        output = get_games()
        self.assertEqual(output['games'], [])   

        # Make sure the get_games method works
        games = player.get_games()
        output = get_games()
        self.assertEqual(output['games'].sort(), games.sort())    

if __name__ == '__main__':
    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)

    user = discord.User
    user.id = os.getenv('ID')
    discord = Discord(url = os.getenv('URL'))
    player = Player(user)    
    unittest.main()
    
    