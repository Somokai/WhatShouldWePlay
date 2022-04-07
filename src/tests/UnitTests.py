import unittest
from discordwebhook import Discord
import time
import json
from dotenv import load_dotenv
import os

load_dotenv()


def get_games():
    testFile = '..\961422844179394580.json'
    with open(testFile, 'r') as jsonFile:
        return json.load(jsonFile)

class TestCommands(unittest.TestCase):

    def test_add(self):
        discord.post(content = "$Add Game1, Game 2")
        time.sleep(1)
        output = get_games()
        self.assertEqual(output['games'], ['Game 2','Game1'])

    def test_list(self):
        discord.post(content = "$list")
        time.sleep(1)

    def test_remove(self):
        discord.post(content = "$remove Game1")
        time.sleep(1)
        output = get_games()
        self.assertEqual(output['games'], ['Game 2'])
        
        discord.post(content = "$REMOVE Game 2")
        time.sleep(1)
        output = get_games()
        self.assertEqual(output['games'], [])        

    def test_list_empty(self):
        discord.post(content = "$list")

if __name__ == '__main__':    
    discord = Discord(url = os.getenv('URL'))
    unittest.main()
    