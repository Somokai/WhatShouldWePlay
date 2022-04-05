import discord
import json
import os
import sys
import logging
from datetime import date
from os.path import isfile
from dotenv import load_dotenv


class Player(object):

    _TEMPLATE = {"games": [], "blacklist": []}

    def __init__(self, user):
        self.user = user
        self.record = self.load_record(user)

    def load_record(self, user):
        if not isfile(f'{user.id}.json'):
            return self.create_record(user)
        else:
            with open(f'{user.id}.json', 'r+') as json_file:
                return json.load(json_file)

    def create_record(self, user):
        with open(f'{user.id}.json', 'a') as json_record:
            json.dump(self._TEMPLATE, json_record)
        logging.info(f'Created a gamelist file for {user}... {user.id}.json')
        return self._TEMPLATE

    def save_record(self):
        with open(f'tmp_{self.user.id}.json', 'w') as json_record:
            json.dump(self.record, json_record)

        os.remove(f'{self.user.id}.json')
        os.rename(f'tmp_{self.user.id}.json', f'{self.user.id}.json')
        logging.info(f'User {self.user}\'s record has been saved')

    def add_games(self, games):
        self.record["games"] = list(set(games + self.record["games"]))
        self.save_record()
        logging.info(
            f'{", ".join(games)} successfully added to {self.user}\'s record.')

    def remove_games(self, games):
        for game in games:
            if game in self.record["games"]:
                self.record["games"].remove(game)

        self.save_record()
        logging.info(
            f'{", ".join(games)} successfully removed from {self.user}\'s record.')

    def get_games(self):
        return self.record["games"]


class WhatshouldWePlayBot(discord.Client):

    def __init__(self):
        self = super().__init__(intents=discord.Intents.default())

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s %(message)s]",
            handlers=[
                logging.FileHandler(f'{date.today()}.log'),
                logging.StreamHandler(sys.stdout)
            ])

    async def on_ready():
        logging.INFO(f'Logged in as user {client.user}')

    async def on_message(self, message):
        if message.author == client.user:
            return

        cmd, msg = message.content.split(' ', 1)

        if cmd not in ['$add', '$remove', '$list']:
            return

        logging.info(f'Message Received from {message.author}: {cmd} {msg}')

        author = message.author

        if cmd == '$add':
            games = [game.strip() for game in msg.split(',')]
            user = Player(author)
            user.add_games(games)
            await message.channel.send(f'{", ".join(games)} added to {author}\'s record')
        elif cmd == '$remove':
            games = [game.strip() for game in msg.split(',')]
            user = Player(author)
            user.remove_games(games)
            await message.channel.send(f'{", ".join(games)} removed from {author}\'s record')
        elif cmd == '$list':
            user = Player(author)
            await message.channel.send(f'{", ".join(user.get_games())}')
        return

    async def on_member_update(prev, cur):

        if prev.activities == cur.activities:
            return

        user = Player(cur)

        if cur.activity.type is discord.ActivityType.playing:
            user.add_games([cur.activity.name])
            logging.info(
                f'User starting playing {cur.activity.name}. Added to gamelist')


if __name__ == '__main__':
    load_dotenv()
    client = WhatshouldWePlayBot()
    client.run(os.getenv('TOKEN'))
