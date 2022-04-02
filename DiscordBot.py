import discord
import json
import os
#if not exists('members.json'):

intents = discord.Intents.all()
client = discord.Client(intents=intents)

with open('token.txt') as file:
    TOKEN = file.read()


textChannels  = []
voiceChannels = []
guildDict = {}

def initialize():
    for channel in client.get_all_channels():
        if str(channel.type) == 'text':
            textChannels.append(channel)
        elif str(channel.type) == 'voice':
            voiceChannels.append(channel)
    
    for guild in client.guilds:
        print(guild.id)
        guildFile = str(guild.id)+'.json'
        if not os.path.exists(guildFile):
            memberDict = {}
            for member in guild.members:
                print(member)
                memberDict[str(member.id)] = []
            with open(guildFile,'w') as outfile:
                json.dump(memberDict, outfile)
            
        with open(guildFile) as json_file:
            guildDict[str(guild.id)] = json.load(json_file)

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    print('Initializing')
    initialize()

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    gameList = guildDict[str(message.guild.id)][str(message.author.id)]

    if message.content.startswith('$add'):
        games = message.content[4:].split(',')
        for game in games:
            game = game.strip()
            if game not in gameList:
                gameList.append(game)
                await message.channel.send('Added: ' + game)
            else:
                await message.channel.send(game + " Already in list.")

    if message.content.startswith('$remove'):
        games = message.content[7:].split(',')
        for game in games:
            game = game.strip()
            if game in gameList:
                gameList.remove(game)
                await message.channel.send('Removed: ' + game)
            else:
                await message.channel.send(game + " Not in list.")

    if message.content.startswith('$list'):
        await message.channel.send('All games: ' + ', '.join(gameList))

    with open(str(message.guild.id) + '.json', 'w') as outFile:
        json.dump(guildDict[str(message.guild.id)], outFile)

client.run(TOKEN)



