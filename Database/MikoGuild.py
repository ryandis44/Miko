'''
This class is responsible for handling all guild data
'''



import discord
import logging

from Database.MySQL import AsyncDatabase
from Database.Redis import RedisCache
from discord.ext.commands import Bot
from misc.misc import sanitize_name
db = AsyncDatabase(__file__)
r = RedisCache(__file__)
LOGGER = logging.getLogger()



class MikoGuild:
    
    def __init__(self) -> None:
        self.guild: discord.Guild = None
        self.client: Bot = None
        
        
        
    def __str__(self) -> str: return f"MikoGuild | {self.guild}"
        
        
        
    async def ainit(self, guild: discord.Guild, client: Bot, check_exists: bool = True) -> None:
        self.guild = guild
        self.client = client
        if check_exists: await self.__exists()
    
    
    
    async def reinit(self) -> None:
        await self.ainit(guild=self.guild, client=self.client)
    
    
    
    async def __exists(self) -> None:
        
        # Check if guild exists
        __rawguild = await db.execute(
            f"SELECT profile,emoji_id,name,owner_id,member_count FROM GUILDS WHERE guild_id='{self.guild.id}'"
        )
        if __rawguild == [] or __rawguild is None:
            
            i = 0
            while True:
                if i>=3: break
                i += 1
                try:
                    await db.execute(
                        "INSERT INTO GUILDS (guild_id, name, owner_id, member_count) VALUES "
                        f"('{self.guild.id}', '{sanitize_name(self.guild.name)}', '{self.guild.owner_id}', '{self.guild.member_count}')"
                    )
                    LOGGER.info(f"Added guild {self.guild.name} ({self.guild.id}) to database.")
                except:
                    
                    # If we fail at inserting the guild, we need to check if the owner exists in the database.
                    # The owner is a foreign key constraint on the GUILDS table, so we need to insert the owner
                    # before the server. We handle this here
                    __tmp = await db.execute(
                        f"SELECT * FROM USERS WHERE user_id='{self.guild.owner_id}'"
                    )
                    if __tmp is None or __tmp == []:
                        await db.execute(
                            "INSERT INTO USERS (user_id, username, is_bot, last_interaction) VALUES "
                            f"('{self.guild.owner_id}', '{sanitize_name(self.guild.owner.name)}', '{str(1) if self.guild.owner.bot else str(0)}', '0')"
                        )
                    else: break
            
        else:
            # Since we requested the guild from the database, and we know it exists,
            # we can assign guild attributes from the database here.
            self.profile_text = __rawguild[0][0]
            self.emoji_id = __rawguild[0][1]
            
            # Update cache of database (i.e. name of server, server owner, etc)
            await self.__update_database(__rawguild)
            
        # Check if guild settings exist. Request settings from
        # database twice only if it does not exist. Else,
        # request settings only once.
        __db_string = (
            "SELECT ymca_green_book_announce_channel,music_channel,big_emojis,greet_new_members,notify_member_leave,"
            "nickname_in_ctx,bruh_react,role_assign "
            f"FROM GUILD_SETTINGS WHERE guild_id='{self.guild.id}'"
        )
        __rawguild_settings = await db.execute(__db_string)
        if __rawguild_settings == [] or __rawguild_settings is None:
            await db.execute(
                "INSERT INTO GUILD_SETTINGS (guild_id) VALUES "
                f"('{self.guild.id}')"
            )
            LOGGER.info(f"Added guild settings for {self.guild.name} ({self.guild.id}) to database.")
            __rawguild_settings = await db.execute(__db_string)
        
        self.ymca_green_book_announce_channel = None if __rawguild_settings[0][0] is None else self.guild.get_channel(int(__rawguild_settings[0][0]))
        self.music_channel = None if __rawguild_settings[0][1] is None else self.guild.get_channel(int(__rawguild_settings[0][1]))
        self.do_big_emojis = True if __rawguild_settings[0][2] == "TRUE" else False
        self.do_greet_new_members = True if __rawguild_settings[0][3] == "TRUE" else False
        self.do_notify_member_leave = True if __rawguild_settings[0][4] == "TRUE" else False
        self.do_nickname_in_ctx = True if __rawguild_settings[0][5] == "TRUE" else False
        self.do_bruh_react = True if __rawguild_settings[0][6] == "TRUE" else False
        self.role_assign = None if __rawguild_settings[0][7] is None else self.guild.get_role(int(__rawguild_settings[0][7]))
    
    
    
    async def __update_database(self, __rawguild: list) -> None:
        update_params = []
        if sanitize_name(self.guild.name) != __rawguild[0][2]: update_params.append(f"name='{sanitize_name(self.guild.name)}'")
        if self.guild.owner_id != __rawguild[0][3]: update_params.append(f"owner_id='{self.guild.owner_id}'")
        if self.guild.member_count != __rawguild[0][4]: update_params.append(f"member_count='{self.guild.member_count}'")
        
        if update_params:
            await db.execute(
                f"UPDATE GUILDS SET {','.join(update_params)} WHERE guild_id='{self.guild.id}'"
            )
            LOGGER.debug(f"Updated guild {self.guild.name} ({self.guild.id}) in database.")
        
        
    
###########################################################################################################################
    
    

    @property
    def guild_settings(self) -> dict:
        return {
            'ymca_green_book_announce_channel': self.ymca_green_book_announce_channel,
            'music_channel': self.music_channel,
            'big_emojis': self.do_big_emojis,
            'greet_new_members': self.do_greet_new_members,
            'notify_member_leave': self.do_notify_member_leave,
            'nickname_in_ctx': self.do_nickname_in_ctx,
            'bruh_react': self.do_bruh_react,
            'role_assign': self.role_assign
        }
    
    
    
    @property
    async def guild_messages(self) -> int:
        count = await r.get(key=f"msg_count:{self.guild.id}", type="STRING")
        if count is None: return 0
        return int(count)
    
    
    
    @property
    async def rename_hell_members(self) -> list:
        val = await db.execute(
            "SELECT user_id FROM USERS WHERE rename_hell=\"TRUE\""
        )
        return [item[0] for item in val] if type(val) is tuple else [val] if val != [] else []
    
    
    
    async def set_role_assign(self, role_id: int = None) -> None:
        if role_id is not None: __str = f"role_assign='{role_id}'"
        else: __str = "role_assign=NULL"
        await db.execute(
            f"UPDATE GUILD_SETTINGS SET {__str} WHERE guild_id='{self.guild.id}'"
        )
    
    
    
    async def remove_user_from_rename_hell(self, user_id: str) -> None:
        await db.execute(
            "UPDATE USER_SETTINGS SET rename_hell='FALSE' WHERE "
            f"user_id='{user_id}'"
        )
    
    
    
    async def increment_message_count(self) -> None:
        count = await r.get(key=f"msg_count:{self.guild.id}", type="STRING") # get it
        if count is None: count = "0" # handle non existing
        count = str(int(count) + 1) # increment it
        await r.set(key=f"msg_count:{self.guild.id}", value=count, type="STRING") # save it