'''
Calling file for raw message edit events
'''



import discord
import logging

from Database.MikoCore import MikoCore
from discord.ext.commands import Bot
LOGGER = logging.getLogger()

async def caller(payload: discord.RawMessageUpdateEvent, client: Bot) -> None:
    mc = MikoCore()
    if not mc.tunables('EVENT_ENABLED_ON_RAW_MESSAGE_EDIT'): return
    
    ch = await client.fetch_channel(payload.channel_id)
    if ch is not None:
        await mc.channel_ainit(ch, client)
        await mc.guild_ainit(ch.guild, client)
        
        if mc.channel.channel_settings['ai_mode'] != "DISABLED" and mc.profile.feature_enabled("AI_MODE"):
            await mc.message.edit_cached_message(payload)