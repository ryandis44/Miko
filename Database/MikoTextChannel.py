'''
This class is responsible for handling all user data
'''



import discord
import logging

from Database.MySQL import AsyncDatabase
from discord.ext.commands import Bot
from misc.misc import sanitize_name
db = AsyncDatabase(__file__)
LOGGER = logging.getLogger()



class MikoTextChannel:
    
    def __init__(self) -> None:
        self.channel: discord.TextChannel|discord.Thread = None
        self.thread: discord.Thread = None
        self.channel_settings: dict = {
            'ai_mode': None,
            'ai_threads': None,
            'karuta_ops': None,
        }
    
    
    
    async def ainit(self, channel: discord.TextChannel|discord.Thread, client: Bot, check_exists: bool = True) -> None:
        
        if channel.type in [discord.ChannelType.public_thread, discord.ChannelType.private_thread, discord.ChannelType.news_thread]:
            self.thread = channel
            self.channel = channel.parent
        else: self.channel = channel
        
        self.client = client
        if check_exists: await self.__exists()
    
    
    
    async def __exists(self) -> None:
        __rawchannel = await db.execute(
            f"SELECT name,channel_id "
            f"FROM TEXT_CHANNELS WHERE channel_id='{self.channel.id}'"
        )
        
        if __rawchannel == [] or __rawchannel is None:
            await db.execute(
                "INSERT INTO TEXT_CHANNELS (guild_id, channel_id, name) VALUES "
                f"('{self.channel.guild.id}', '{self.channel.id}', '{sanitize_name(self.channel.name)}')"
            )
            LOGGER.info(f"Added {self.channel.name} in guild {self.channel.guild} to database")
        
        else: await self.__update_database(__rawchannel)
        
        
        __cols = [col for col, value in self.channel_settings.items()]
        __db_string = (
            f"SELECT `{'`, `'.join(__cols)}` "
            f"FROM CHANNEL_SETTINGS WHERE channel_id='{self.channel.id}'"
        )
        __rawchannel_settings = await db.execute(__db_string)
        if __rawchannel_settings == [] or __rawchannel_settings is None:
            await db.execute(
                "INSERT INTO CHANNEL_SETTINGS (channel_id) VALUES "
                f"('{self.channel.id}')"
            )
            LOGGER.info(f"Added {self.channel.name} settings in guild {self.channel.guild} to database")
            __rawchannel_settings = await db.execute(__db_string)
        
        # unpack values from the database and assign them
        for i, col in enumerate(__cols):
            self.channel_settings[col] = __rawchannel_settings[0][i]
    
    
    
    async def __update_database(self, __rawchannel: list) -> None:
        update_params = []
        if sanitize_name(self.channel.name) != __rawchannel[0][0]: update_params.append(f"name='{sanitize_name(self.channel.name)}'")
        
        if update_params:
            await db.execute(
                f"UPDATE TEXT_CHANNELS SET {', '.join(update_params)} WHERE channel_id='{self.channel.id}'"
            )
            LOGGER.debug(f"Updated {self.channel.name} in guild {self.channel.guild} in database")



###########################################################################################################################
    
    
    
    async def set_ai_mode(self, mode: str) -> None:
        mode = str(mode).upper()
        await db.execute(
            f"UPDATE CHANNEL_SETTINGS SET ai_mode='{mode}' WHERE channel_id='{self.channel.id}'"
        )
        self.ai_mode = mode