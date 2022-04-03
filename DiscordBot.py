import discord
import json
import os
import glob
# if not exists('members.json'):

intents = discord.Intents.all()
client = discord.Client(intents=intents)

textChannels = []
voiceChannels = []
guildFiles = glob.glob('*.json')


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
            with open(guildFile, 'w') as outfile:
                json.dump(memberDict, outfile)
        else:
            with open(guildFile, 'r') as jsonFile:
                guildDict = json.load(jsonFile)
            for member in guild.members:
                if member not in guildDict:
                    print(member)
                    guildDict[member.id] = []
            with open(guildFile, 'w') as outfile:
                json.dump(guildDict, outfile)


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    print('Initializing')
    initialize()


@client.event
async def on_message(message):
    if message.author == client.user:
        return
      
    commands = ['$add', '$remove', '$list']

    msg = str(message.content)
    if msg.split(' ')[0] not in commands:
        return
      
    guildFiles = glob.glob('*.json')

    author = str(message.author.id)
    # This should only populate gameLists for guilds the user is in.
    gameLists = []
    if str(message.channel.type) == 'private':
        for guildFile in guildFiles:
            with open(guildFile,'r') as json_file:
                guildDict = json.load(json_file)
            if author in guildDict:
                gameLists.append(guildDict[author])
    else:
        with open(str(message.guild.id)+'.json','r') as json_file:
            guildDict = json.load(json_file)
        gameLists.append(guildDict[author])

    if message.content.startswith('$add'):
        games = message.content[4:].split(',')
        for gameList in gameLists:
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
            for gameList in gameLists:
                if game in gameList:
                    gameList.remove(game)
                    await message.channel.send('Removed: ' + game)
                else:
                    await message.channel.send(game + " Not in list.")

    if message.content.startswith('$list'):
        for gameList in gameLists:
            await message.channel.send('All games: ' + ', '.join(gameList))

    if str(message.channel.type) == 'private':
        for ind in range(len(gameLists)):
            with open(guildFiles[ind], 'r') as outFile:
                guildDict = json.load(outFile)
                guildDict[author] = gameLists[ind]
            with open(guildFiles[ind], 'w') as outFile:
                json.dump(guildDict, outFile)
    else:
        with open(str(message.guild.id) + '.json', 'r') as outFile:
            guildDict = json.load(outFile)
            guildDict[author] = gameLists[0]
        with open(guildFiles[0], 'w') as outFile:
            json.dump(guildDict, outFile)

@client.event
async def on_member_update(prev, cur):

    guildFile = str(cur.guild.id) + '.json'
    if hasattr(cur.activity, 'name'):
        game = cur.activity.name
    else:
        game = str(cur.activity)

    if game == 'None':
        return

    with open(guildFile, 'r') as jsonFile:
        guildDict = json.load(jsonFile)
        if game not in guildDict[str(cur.id)]:
            guildDict[str(cur.id)].append(game)
            print('Added: ' + game +  ' to ' +  str(cur) +'\'s game list in ' + str(cur.guild))

    with open(guildFile, 'w') as outFile:
        json.dump(guildDict, outFile)

client.run(os.getenv('TOKEN'))

