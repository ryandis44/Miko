# Miko Bot main file
from Database.database_class import connect_pool
from tunables import tunables_init, tunables, GLOBAL_EMBED_COLOR, tunables_refresh
tunables_init()

import tracemalloc
tracemalloc.start()

import time
import sys
from OpenAI.ai import MikoGPT
import asyncio
import os
import discord
import re
import random
import signal
from Presence.Objects import PresenceUpdate
from Plex.embeds import info_anime, info_dubbed, info_quality, info_subbed, plex_update_2_28_23, plex_update_2_3
from misc.embeds import plex_requests_embed
from dpyConsole import Console
from discord.utils import get
from discord.ext import commands
from dotenv import load_dotenv
from Database.GuildObjects import MikoGuild, MikoMember, MikoMessage, RawMessageUpdate, fetch_playtime_sessions
from Emojis.emoji_generator import regen_guild_emoji
from async_processes import heartbeat, set_async_client, MaintenanceThread
from utils.HandleInterrupt import interrupt, nullify_restore_time
from Voice.track_voice import fetch_voicetime_sessions, process_voice_state
from utils.parse_inventory import check_for_karuta, parse_inventory
from Database.RedisCache import connect_redis
from Music.LavalinkClient import AUDIO_SESSIONS
from Polls.UI import active_polls
from Database.RedisCache import RedisCache
r = RedisCache('main.py')


msg_count = 0



load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.all()
client = discord.Client(intents=intents)
client = commands.Bot(command_prefix = [os.getenv('CMD_PREFIX1'), os.getenv('CMD_PREFIX2')], case_insensitive=True, help_command=None, intents=intents)
console = Console(client)
running = True

maintenance = MaintenanceThread()
maintenance.start()

def thread_kill(one=None, two=None):
    global running
    running = False
    print("Shutting down...")
    interrupt()
    print("Graceful shutdown complete. Goodbye.")
    os._exit(0)
signal.signal(signal.SIGINT, thread_kill)

@console.command()
async def shutdown():
    thread_kill()

# Cannot be in a cog because client object is not available in
# cog (API limitation)
@console.command()
async def say(channel=None, *msg):
    usage = "Usage: <channel ID> <msg>"
    if channel is None or len(msg) == 0 or not channel.isdigit():
        print(usage)
        return
    channel = client.get_channel(int(channel))
    await channel.send(' '.join(msg))

@console.command()
async def msg(user: discord.User, *msg):
    print(f"Sent {user} {' '.join(msg)}")
    await user.send(' '.join(msg))

@console.command()
async def leave(guild: discord.Guild):
    await guild.leave()
    print(f"Left {guild}")

@console.command()
async def edit(channel=None, msg_id=None, *msg):
    usage = "Usage: <channel ID> <msg ID> <msg>"
    if channel is None or len(msg) == 0 or not channel.isdigit() or msg_id is None or not msg_id.isdigit():
        print(usage)
        return
    channel = client.get_channel(int(channel))

    async for message in channel.history(limit=100):
        if str(message.id) == str(msg_id):

            msg = ' '.join(msg)
            msg = msg.split("|")

            await message.edit(content='\n'.join(msg))

@console.command()
async def count(guild: discord.Guild):
    print(f"Counting all messages in {guild}")

@console.command()
async def embed(choice=None, channel=None):
    if choice is None or channel is None:
        print("Usage: <embed> <channel ID>")
        return

    channel = client.get_channel(int(channel))
    match choice:

        case 'quality':
            file = discord.File("Plex/Images/quality.png")
            await channel.send(embed=info_quality(), file=file)
        case 'anime':
            await channel.send(embed=info_anime())
        case 'subbed':
            file = discord.File("Plex/Images/subbed.png")
            await channel.send(embed=info_subbed(), file=file)
        case 'dubbed':
            file = discord.File("Plex/Images/dubbed.png")
            await channel.send(embed=info_dubbed(), file=file)
        case 'request':
            await channel.send(embed=plex_requests_embed())
        case '1-10-23':
            await channel.send(embed=plex_update_2_3(), content="<@&1001733271459221564>")
        case '2-28-23':
            file = discord.File("Plex/Images/popular_info.png")
            await channel.send(embed=plex_update_2_28_23(), file=file, content="<@&1001733271459221564>")
        case 'expo-info-23':
            embed = discord.Embed (
                title = tunables('ANIME_EXPO_2023_INFO_EMBED_TITLE'),
                url=tunables('ANIME_EXPO_2023_INFO_EMBED_URL'),
                color = GLOBAL_EMBED_COLOR,
                description=tunables('ANIME_EXPO_2023_INFO_EMBED_DESCRIPTION')
            )
            embed.set_thumbnail(url=tunables('ANIME_EXPO_2023_INFO_EMBED_THUMBNAIL_URL'))
            await channel.send(embed=embed)
        case _:
            print("Embed not found")




@client.event
async def on_guild_join(guild: discord.Guild):
    if not tunables('EVENT_ENABLED_ON_GUILD_JOIN'): return
    g = MikoGuild(guild=guild, client=client)
    await g.ainit()

@client.event
async def on_member_join(member: discord.Member):
    if not tunables('EVENT_ENABLED_ON_MEMBER_JOIN'): return
    if not running: return
    u = MikoMember(user=member, client=client)
    await u.ainit()
            
@client.event
async def on_raw_message_delete(payload: discord.RawMessageDeleteEvent):
    if not tunables('EVENT_ENABLED_ON_RAW_MESSAGE_DELETE'): return
    await r.delete(key=f"m:{payload.message_id}")
    poll = active_polls.get_val(str(payload.message_id))
    if poll is None: return
    poll.terminate()

# Responsible for handling member leaving guild
@client.event
async def on_raw_member_remove(payload: discord.RawMemberRemoveEvent):
    if not tunables('EVENT_ENABLED_ON_RAW_MEMBER_REMOVE'): return
    if payload.user.id == client.user.id:
        g = MikoGuild(guild=payload.user.guild, client=client)
        await g.handle_leave_guild()
        return

    if not running: return
    if payload.user.pending: return
    g = MikoGuild(guild=None, client=client, guild_id=payload.guild_id)
    await g.ainit()

    
    temp = []
    temp.append(f"<@{payload.user.id}>『`{payload.user}`』left")
    match await g.status:

        case "THEBOYS":
            if client.user.id != 1017998983886545068: return
            guild = client.get_guild(payload.guild_id)
            channel = guild.system_channel
            if channel is None: return

            match random.randint(0, 6):
                case 0: temp.append(" :pray:")
                case 1: temp.append(". Thank God")
                case 2: temp.append(". Finally!")
                case 3: temp.append(". Hector scared them off")
                case 4: temp.append(". Good riddance")
                case 5: temp.append(". Oh no! Anyway...")
                case 6: temp.append(". I thought they would never leave... :triumph:")

            await channel.send(''.join(temp))
        
        case "YMCA":
            channel = client.get_guild(payload.guild_id).system_channel
            await channel.send(''.join(temp))


# Responsible for updating username history
@client.event
async def on_member_update(before: discord.Member, cur: discord.Member):
    if not tunables('EVENT_ENABLED_ON_MEMBER_UPDATE'): return
    if not running: return
    u = MikoMember(user=cur, client=client)
    await u.ainit()


# Responsible for keeping guild emojis up-to-date
@client.event
async def on_guild_update(before: discord.Guild, after: discord.Guild):
    if not tunables('EVENT_ENABLED_ON_GUILD_UPDATE'): return
    if not running: return
    g = MikoGuild(guild=after, client=client)
    await g.ainit()
    if before.icon != after.icon:
        await regen_guild_emoji(client=client, guild=after)


# Playtime
@client.event
async def on_presence_update(before: discord.Member, cur: discord.Member):
    if not tunables('EVENT_ENABLED_ON_PRESENCE_UPDATE'): return
    if not running: return
    u = MikoMember(user=cur, client=client)
    await u.ainit()
    await u.increment_statistic('PRESENCE_UPDATES')
    p = PresenceUpdate(u=u, b=before, a=cur)
    await p.ainit()


# Voicetime
@client.event
async def on_voice_state_update(member: discord.Member, bef: discord.VoiceState, cur: discord.VoiceState):
    if not tunables('EVENT_ENABLED_ON_VOICE_STATE_UPDATE'): return
    u = MikoMember(user=member, client=client)
    await u.ainit()
    
    # if bot is removed from voice channel, cleanup and delete voice_client object
    # this prevents the bot from thinking it is still in vc after being
    # disconnected
    if bef.channel is not None and cur.channel is None and member == client.user:
        try: sesh = AUDIO_SESSIONS[member.guild.id]
        except: sesh = None
        if sesh is not None:
            await sesh.stop()
    
    if (await u.profile).feature_enabled('TRACK_VOICETIME') != 1: return
    if not running: return
    await u.increment_statistic('VOICE_STATE_UPDATES')
    if member.bot: return # do not track bots
    await process_voice_state(u=u, bef=bef, cur=cur)

@client.event
async def on_raw_message_edit(payload: discord.RawMessageUpdateEvent) -> None:
    if not tunables('EVENT_ENABLED_ON_RAW_MESSAGE_EDIT'): return
    await RawMessageUpdate(payload=payload).ainit()

@client.event
async def on_message(message: discord.Message):
    if not tunables('EVENT_ENABLED_ON_MESSAGE'): return
    if not running: return
    mm = MikoMessage(message=message, client=client)
    try: await mm.ainit()
    except: return
    if (await mm.channel.profile).feature_enabled('MESSAGE_HANDLING') != 1:
        await client.process_commands(message)
        return
    else: await client.process_commands(message)

    
    if message.content.lower().startswith(f"{os.getenv('CMD_PREFIX1')}rt") and await mm.user.bot_permission_level >= 5:
        await message.channel.send("Fetching tunables from database...")
        await tunables_refresh()
        await message.channel.send("Tunables refreshed.")

    await mm.handle_leveling()
    if await mm.ugly_ass_sticker_removal(): return
    if await mm.handle_big_emojis(): return # Deletes message. Returns true if message deleted.
    if await mm.handle_instagram_reel_links(): return # Also deletes message
    await mm.handle_persistent_player_reposition()
    await mm.handle_rename_hell()
    await mm.handle_bruh_react()
    await mm.handle_clown_react()
    await mm.handle_react_all()


    if (await mm.channel.profile).feature_enabled('KARUTA_EXTRAS') == 1:
        karuta_id = 646937666251915264 #Karuta bot ID
        # Analyze embed from karuta bot, retrieve inventory items from embed, and calculate values
        # for trades according to hard coded bot IDs
        bot_ids = [903469976759959613, 981078995539988500, 511312859523973140, 957484905590325281, 954585066619682906, 747498003601817781]
        if message.author.id in bot_ids and message.content.lower() == 'ki' and (message.channel.name == 'karuta-mute-me' or message.channel.name == 'baruta-kots' or message.channel.name == 'hectorless-karuta'):
            embed_message = await client.wait_for('message', timeout=15, check=check_for_karuta(karuta_id))
            embed_dict = embed_message.embeds[0].to_dict()
            reply_message = parse_inventory(embed_dict['description'], message)
            await message.reply(reply_message)


        # React with pepe clown emoji to any karuta commands sent in non-karuta channels
        # and deletes messages in karuta channels matched in 'del_karuta_commands'
        karuta_channels = [
            client.get_channel(890644443575771166), #0 > karuta-mute-me
            client.get_channel(963928489248063539) #1 > baruta-kots
        ]
        del_karuta_commands = ['kv']
        for command in tunables('KARUTA_COMMANDS').split():
            reg_ex = re.escape(command) + r" (.*)"
            if re.match(reg_ex, message.content.lower()) or command == message.content.lower():
                if message.channel not in karuta_channels:
                    await message.add_reaction('<:clown:903162517365330000>')
                if message.channel == karuta_channels[0] or message.channel == karuta_channels[2]: # karuta-mute-me
                    if command in del_karuta_commands:
                        await message.delete()

    '''
    # Determine if message sent is in bot channel, and if so, determine whether it is
    # from karuta and is a drop
    img_ext = ['.jpg', '.webp', '.png', '.jpeg']
    drop_regex = r"<@\d{15,22}> is dropping [3-4] cards!"
    if message.channel.name == 'baruta-kots' and message.author.id == karuta_id:
        if re.match(drop_regex, message.content.lower()):
            if len(message.attachments) > 0:
                for ext in img_ext:
                    if (message.attachments[0].url.lower().endswith(ext)):
                        await asyncio.sleep(5)
                        await message.add_reaction('<:verifiedblue:963658235628359710>')
                        break
    '''
    await MikoGPT(mm=mm).ainit()
    # elif (await mm.channel.profile).feature_enabled('REPLY_TO_MENTION') == 1:
    #         await message.reply(
    #             content=f"Please use {tunables('SLASH_COMMAND_SUGGEST_HELP')} for help.",
    #             silent=True
    #         )
    
    # # Respond to being mentioned
    # if len(message.content) > 0 and str(client.user.id) in message.content.split()[0] and message.author.id != client.user.id or \
    #     (message.reference is not None and message.reference.resolved is not None and \
    #         message.reference.resolved.author.id == client.user.id):
        
    #     if (await mm.channel.profile).feature_enabled('CHATGPT') == 1:

    #         # Send help menu if only @ ing Miko
    #         if len(message.content.split()) <= 1 and message.content == f"<@{str(client.user.id)}>":
    #             await message.reply(
    #                 content=f"Please use {tunables('SLASH_COMMAND_SUGGEST_HELP')} for help.",
    #                 silent=True
    #             )
    #             return


        
    #     # Basic response
    #     elif (await mm.channel.profile).feature_enabled('REPLY_TO_MENTION') == 1:
    #         await message.reply(
    #             content=f"Please use {tunables('SLASH_COMMAND_SUGGEST_HELP')} for help.",
    #             silent=True
    #         )

    return


async def load_extensions():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await client.load_extension(f'cogs.{filename[:-3]}')

async def load_extensions_on_ready():
    for filename in os.listdir('./cogs_on_ready'):
        if filename.endswith('.py'):
            await client.load_extension(f'cogs_on_ready.{filename[:-3]}')

async def load_extensions_console():
    for filename in os.listdir('./cogs_console'):
        if filename.endswith('.py'):
            console.load_extension(f'cogs_console.{filename[:-3]}')

async def main():
    print('bot online')
    await connect_pool()
    await connect_redis()
    asyncio.create_task(heartbeat())
    async with client:
        await load_extensions()
        console.start()
        await load_extensions_console()
        await client.start(TOKEN)

initial = True
@client.event
async def on_ready():
    global initial
    # await client.load_extension(f'MusicCog.MusicPlayer')
    await load_extensions_on_ready()
    await client.load_extension(f'Leveling.LevelCog')
    await client.load_extension(f'Plex.PlexCog')
    set_async_client(client)
    if initial:
        initial = False
        print("\nAttempting to restore playtime sessions...")
        await fetch_playtime_sessions(client=client)
        print("\nAttempting to restore voicetime sessions...")
        await fetch_voicetime_sessions(client=client)
        print("\n")
        nullify_restore_time()

asyncio.run(main())