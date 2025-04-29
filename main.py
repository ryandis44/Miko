'''
Miko! Discord bot main file. This file is responsible for starting the bot, and loading all the necessary libraries and files.
Any extra features are referenced by main.py, and are imported as needed. No core functionality is implemented in this file.
'''

import asyncio
import discord
import logging # used for logging messages to the console and log file
import mafic # music player
import os # used for exiting the program without error messages
import signal # used for handling shutdown signals (ctrl+c)

from cogs_cmd_on_ready.MusicPlayer.Backend import track_end
from discord.ext import commands
from dotenv import load_dotenv # load environment variables from .env file
from dpyConsole import Console # console used for debugging, logging, and shutdown via control panel
from Database.MySQL import connect_pool # connect to the database
from Database.Redis import connect_redis # connect to the redis cache
from Database.tunables import tunables_init, tunables # tunables used by the bot
from Events.MemberJoin.Core import caller as on_member_join_caller # core member join event handler
from Events.Message.Core import caller as on_message_caller # core message event handler
from Events.Presence.Core import caller as on_presence_update_caller # core presence event handler
from Events.RawMemberRemove.Core import caller as on_raw_member_remove_caller # core raw member remove event handler
from Events.RawMessageEdit.Core import caller as on_raw_message_edit_caller # core raw message edit event handler
from Events.RawMessageDelete.Core import caller as on_raw_message_delete_caller # core raw message delete event handler
from Events.VoiceStateUpdate.Core import caller as on_voice_state_update_caller # core voice state update event handler



###########################################################################################################################



'''
Set up logger and load variables
'''

log_level = os.getenv('LOG_LEVEL', 20)
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.WARNING if log_level is None else int(log_level)) # default log level is WARNING
handler = logging.FileHandler(filename='miko.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s:%(filename)s:%(lineno)s: %(message)s'))
LOGGER.addHandler(handler)

tunables_init()
load_dotenv() # load environment variables from .env file



###########################################################################################################################



'''
Create bot class and define bot intents. These are used to determine what events the bot will receive.
Additionally setup music player and on_ready event.
'''
LAN_IP = os.getenv('LAN_IP')
class Bot(commands.Bot):
    def __init__(self) -> None:
        intents: discord.Intents = discord.Intents.all()
        super().__init__(command_prefix=tunables("COMMAND_PREFIX"), intents=intents, case_insensitive=True, help_command=None)
        self.first_run = True
        self.pool = mafic.NodePool(self)
    
    
    
    async def on_ready(self) -> None:
        if self.first_run:
            await self.pool.create_node(
                host=LAN_IP,
                port=2333,
                label="MAIN",
                password=tunables('LAVALINK_PASSWORD'),
            )
        
        LOGGER.log(level=logging.INFO, msg=f'Logged in as {client.user} {client.user.id}')
        print('bot online') # for pterodactyl console for online status
        await client.change_presence(activity=discord.Game(name=tunables("ACTIVITY_STATUS")))
        await load_cogs_cmd_on_ready()
        self.first_run = False

client = Bot()
console = Console(client=client)



###########################################################################################################################



'''
Handle shutdown signal from keyboard and console.
'''

def thread_kill(one=None, two=None):
    print("Shutting down...")
    LOGGER.log(level=logging.CRITICAL, msg="Shutting down...")
    print("Graceful shutdown complete. Goodbye.")
    LOGGER.log(level=logging.CRITICAL, msg="Graceful shutdown complete. Goodbye.")
    os._exit(0)
signal.signal(signal.SIGINT, thread_kill)

@console.command()
async def shutdown(): thread_kill() # pterodactyl panel shutdown command



###########################################################################################################################



'''
Events are detected here and passed to caller
functions for processing
Events are located in the Events directory
'''

@client.event
async def on_message(message):
    try: await on_message_caller(message, client)
    except Exception as e: LOGGER.error(f"Error in on_message: {e}")



@client.event
async def on_presence_update(previous, current):
    try: await on_presence_update_caller(previous, current, client)
    except Exception as e: LOGGER.error(f"Error in on_presence_update: {e}")



@client.event
async def on_member_join(member):
    try: await on_member_join_caller(member, client)
    except Exception as e: LOGGER.error(f"Error in on_member_join: {e}")



@client.event
async def on_raw_member_remove(payload):
    try: await on_raw_member_remove_caller(payload, client)
    except Exception as e: LOGGER.error(f"Error in on_raw_member_remove: {e}")



@client.event
async def on_voice_state_update(member, before, after):
    try: await on_voice_state_update_caller(member, before, after, client)
    except Exception as e: LOGGER.error(f"Error in on_voice_state_update: {e}")



@client.event
async def on_raw_message_edit(payload):
    try: await on_raw_message_edit_caller(payload, client)
    except Exception as e: LOGGER.error(f"Error in on_raw_message_edit: {e}")



@client.event
async def on_raw_message_delete(payload):
    try: await on_raw_message_delete_caller(payload, client)
    except Exception as e: LOGGER.error(f"Error in on_raw_message_delete: {e}")



@client.listen()
async def on_track_end(event):
    try: await track_end(event)
    except Exception as e: LOGGER.error(f"Error in on_track_end: {e}")



###########################################################################################################################



'''
Load all cogs from the cogs directories
'''

async def load_cogs_text():
    for filename in os.listdir('./cogs_text'):
        try:
            if filename.endswith('.py'):
                await client.load_extension(f'cogs_text.{filename[:-3]}')
                LOGGER.log(level=logging.DEBUG, msg=f'Loaded text cog: {filename[:-3]}')
        except Exception as e:
            LOGGER.error(f'Failed to load text cog: {filename[:-3]} | {e}')   
    LOGGER.log(level=logging.DEBUG, msg='All text cogs loaded.')

# Cmd cogs only load the 'cog.py' file in each directory
# This is because command cogs are typically more complex
# than text cogs and have a larger backend
async def load_cogs_cmd():
    for dir in os.listdir('./cogs_cmd'):
        for filename in os.listdir(f'./cogs_cmd/{dir}'):
            try:
                if filename != 'cog.py': continue
                await client.load_extension(f'cogs_cmd.{dir}.{filename[:-3]}')
                LOGGER.log(level=logging.DEBUG, msg=f'Loaded cmd cog: {dir}/{filename[:-3]}')
            except Exception as e:
                LOGGER.error(f'Failed to load cmd cog: {filename[:-3]} | {e}')   
    LOGGER.log(level=logging.DEBUG, msg='All cmd cogs loaded.')
    
async def load_cogs_cmd_on_ready():
    for dir in os.listdir('./cogs_cmd_on_ready'):
        for filename in os.listdir(f'./cogs_cmd_on_ready/{dir}'):
            try:
                if filename != 'cog.py': continue
                await client.load_extension(f'cogs_cmd_on_ready.{dir}.{filename[:-3]}')
                LOGGER.log(level=logging.DEBUG, msg=f'Loaded cmd cog on ready: {dir}/{filename[:-3]}')
            except Exception as e:
                LOGGER.error(f'Failed to load cmd cog on ready: {filename[:-3]} | {e}')   
    LOGGER.log(level=logging.DEBUG, msg='All cmd cogs on ready loaded.')

async def load_cogs_console():
    for filename in os.listdir('./cogs_console'):
        try:
            if filename.endswith('.py'):
                console.load_extension(f'cogs_console.{filename[:-3]}')
                LOGGER.log(level=logging.DEBUG, msg=f'Loaded console cog: {filename[:-3]}')
        except Exception as e:
            LOGGER.error(f'Failed to load console cog: {filename[:-3]} | {e}')
    LOGGER.log(level=logging.DEBUG, msg='All console cogs loaded.')



###########################################################################################################################



'''
Start the bot
'''

async def main() -> None:
    async with client:
        await load_cogs_text()
        await load_cogs_cmd()
        console.start()
        await connect_pool()
        await connect_redis()
        # await load_cogs_console()
        await client.start(os.getenv('DISCORD_TOKEN'))


asyncio.run(main())