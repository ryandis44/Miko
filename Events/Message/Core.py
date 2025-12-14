'''
Calling file for all message events
'''



import discord
import logging

from Database.MikoCore import MikoCore
from discord.ext.commands import Bot
from Events.Message.BigEmojis import big_emojis
from Events.Message.BruhReact import bruh_react
from Events.Message.IncrementMessageCount import increment_guild_message_count
from Events.Message.KarutaOps import karuta_ops
from Events.Message.MusicPlayerReposition import reposition_music_player
from Events.Message.RenameHell import rename_hell
from Events.Message.ReplyToMention import reply_to_mention
from GenerativeAI.Core import GenerativeAI
LOGGER = logging.getLogger()

async def caller(message: discord.Message, client: Bot) -> None:
    
    # ephemeral messages and DMs are not processed
    if message.guild is None: return
    
    mc = MikoCore()
    if mc.tunables('PROCESS_TEXT_COMMANDS'): await client.process_commands(message) # discord.py function for handling all text commands
    if not mc.tunables('EVENT_ENABLED_ON_MESSAGE'): return
    await mc.message_ainit(message=message, client=client)
    
    try:
        if await reposition_music_player(mc): return # reposition music player if applicable
    except Exception as e: LOGGER.error(f"Error in reposition_music_player: {e}")
    
    try:
        if await big_emojis(mc): return # do not process message further if big emoji is created
    except Exception as e: LOGGER.error(f"Error in big_emojis: {e}")
    
    try: await increment_guild_message_count(mc) # +1 to guild msgs
    except Exception as e: LOGGER.error(f"Error in increment_guild_message_count: {e}")
    
    try: await rename_hell(mc) # 'rename_hell' user attribute : bool
    except Exception as e: LOGGER.error(f"Error in rename_hell: {e}")
    
    try: await reply_to_mention(mc) # reply to mention if applicable
    except Exception as e: LOGGER.error(f"Error in reply_to_mention: {e}")
    
    try: await bruh_react(mc) # BRUH_REACT_WORDS in tunables
    except Exception as e: LOGGER.error(f"Error in bruh_react: {e}")
    
    try: await karuta_ops(mc) # miscellaneous karuta operations
    except Exception as e: LOGGER.error(f"Error in karuta_ops: {e}")
    
    try: await GenerativeAI(mc).ainit() # generative AI
    except Exception as e: LOGGER.error(f"Error in GenerativeAI: {e}")