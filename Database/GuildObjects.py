import asyncio
import datetime
from io import BytesIO
import random
import re
import copy
import time
import aiohttp
import discord
from Database.UserAttributes import Playtime
from Music.LavalinkClient import AUDIO_SESSIONS
from Database.database_class import AsyncDatabase
from Database.RedisCache import RedisCache
from Leveling.LevelClass import LevelClass
# from Pets.PetClass import PetOwner
# from Tokens.TokenClass import Token
from Emojis.emoji_generator import get_emoji_url, get_guild_emoji
from Presence.Objects import PresenceUpdate
from YMCA.Checklist.Objects import Checklist
from misc.embeds import help_embed
from misc.holiday_roles import get_holiday
from misc.misc import emojis_1to10, generate_nickname, react_all_emoji_list, today
from tunables import *
ago = AsyncDatabase("Database.GuildObjects.py")
r = RedisCache('Database.GuildObjects.py')

CHECK_LOCK = {}

def check_lock(key) -> asyncio.Lock:
        val = CHECK_LOCK.get(key)
        
        if val is None:
            lock = asyncio.Lock()
            CHECK_LOCK[key] = {
                'at': int(time.time()),
                'lock': lock
            }
            return lock
        
        val['at'] = int(time.time())
        return val['lock']

def lock_status(key) -> bool:
    val = CHECK_LOCK.get(key)
    if val is None: return False
    return val['lock'].locked()

class MikoGuild():

    def __init__(self, guild: discord.Guild, client: discord.Client, guild_id: int = None, check_exists=True, check_exists_guild=True):
        if guild_id is None: self.guild = guild
        else: self.guild = client.get_guild(int(guild_id))
        self.client = client
        self.log_channel = client.get_channel(1073509692363517962) # miko-logs channel in The Boys Hangout

    async def ainit(self, check_exists: bool = True, skip_if_locked: bool = False):
        if check_exists and \
            not (skip_if_locked and lock_status(key=self.guild.id)):
            async with check_lock(key=self.guild.id):
                await self.__exists()

    def __str__(self):
        return f"{self.guild} | MikoGuild Object"

    @property
    async def __last_updated(self) -> int:
        sel_cmd = f"SELECT last_updated FROM SERVERS WHERE server_id='{self.guild.id}'"
        val = await ago.execute(sel_cmd)
        if val is not None and val != []: return int(val)
        print(f"Error when checking 'last_updated' in MikoGuild object: {val} | {self.guild.name} | {self.guild.id} | {int(time.time())}")
        return 1
    @property
    async def guild_messages(self) -> int:
        sel_cmd = (
            "SELECT SUM(count) FROM USER_MESSAGE_COUNT WHERE "
            f"server_id='{self.guild.id}'"
        )
        val = await ago.execute(sel_cmd)
        if val is None or val == []: return 0
        return int(val)
    @property
    async def guild_messages_nobots(self) -> int:
        sel_cmd = (
            "SELECT SUM(mc.count) FROM USER_MESSAGE_COUNT AS mc "
            "INNER JOIN USERS AS u ON "
            "(mc.user_id=u.user_id AND mc.server_id=u.server_id AND u.is_bot!='TRUE') WHERE "
            f"mc.server_id='{self.guild.id}'"
        )
        val = await ago.execute(sel_cmd)
        if val is None or val == []: return 0
        return int(val)
    @property
    async def guild_messages_today(self) -> int:
        sel_cmd = (
            "SELECT messages_today FROM SERVERS WHERE "
            f"server_id='{self.guild.id}'"
        )
        val = await ago.execute(sel_cmd)
        if val == [] or val is None: return 0
        if await self.__last_updated >= today(): return int(val)
        return 0
    @property
    async def status(self) -> str:
        sel_cmd = f"SELECT status FROM SERVERS WHERE server_id={self.guild.id}"
        val: str = await ago.execute(sel_cmd)
        if val == []: return None
        return val.upper()
    @property
    async def music_channel(self) -> discord.TextChannel:
        sel_cmd = f"SELECT music_channel FROM SERVERS WHERE server_id='{self.guild.id}'"
        val = await ago.execute(sel_cmd)
        if val is None or val == []: return None
        return self.guild.get_channel(int(val))
    @property
    async def emoji(self) -> discord.Emoji:
        return await get_guild_emoji(self.client, self.guild)
    @property
    async def top_ten_total_messages_nobots(self):
        val = await ago.execute(
            "SELECT cnt,user_id FROM ("
            "SELECT grouped.*, ROW_NUMBER() OVER ("
            "PARTITION BY grouped.server_id ORDER BY grouped.cnt DESC) AS row "
            "FROM ("
            "SELECT mc.server_id, mc.user_id, SUM(mc.count) AS cnt "
            "FROM USER_MESSAGE_COUNT AS mc "
            "INNER JOIN USERS AS u ON u.user_id=mc.user_id AND mc.server_id=u.server_id AND u.is_bot!='TRUE' "
            f"WHERE mc.server_id='{self.guild.id}' "
            "GROUP BY mc.user_id, mc.server_id) AS grouped) AS ranked "
            "ORDER BY cnt DESC LIMIT 10"
        )
        if val == [] or val is None: return None
        return val
    @property
    async def nickname_in_ctx(self) -> bool:
        val = await ago.execute(
            "SELECT nickname_in_ctx FROM SERVERS WHERE "
            f"server_id='{self.guild.id}'"
        )
        if val == "TRUE" and tunables('NICKNAME_IN_CONTEXT'): return True
        return False
    @property
    async def guild_do_big_emojis(self) -> bool:
        val = await ago.execute(
            "SELECT big_emojis FROM SERVERS WHERE "
            f"server_id='{self.guild.id}'"
        )
        if val == "FALSE" or (await self.profile).feature_enabled('BIG_EMOJIS') != 1: return False
        return True
    @property
    async def profile(self) -> GuildProfile:
        return tunables(f'GUILD_PROFILE_{await self.status}')
    
    
    
    # REDO THIS AT SOME POINT
    @property
    async def renamehell_members(self) -> list:
        val = await ago.execute(
            "SELECT user_id FROM USERS WHERE rename_any_true_false=\"TRUE\" "
            f"AND server_id='{self.guild.id}'"
        )
        return [item[0] for item in val] if type(val) is tuple else [val] if val != [] else []
    #########################
    
    
    
    @property
    async def clown_react_users(self) -> list:
        val = await ago.execute(
            "SELECT user_id FROM USERS WHERE react_true_false=\"TRUE\" AND "
            f"server_id='{self.guild.id}'"
        )
        return [item[0] for item in val] if type(val) is tuple else [val] if val != [] else []
    @property
    async def react_all_users(self) -> list:
        val = await ago.execute(
            "SELECT user_id FROM USERS WHERE react_all_true_false=\"TRUE\" AND "
            f"server_id='{self.guild.id}'"
        )
        
        return [item[0] for item in val] if type(val) is tuple else [val] if val != [] else []
    @property
    async def bot_list(self) -> list:
        val = await ago.execute(
            "SELECT user_id FROM USERS WHERE is_bot=\"TRUE\" "
            f"AND server_id='{self.guild.id}'"
        )
        return [item[0] for item in val] if type(val) is tuple else [val] if val != [] else []
    @property
    async def rename_users(self) -> list:
        val = await ago.execute(
            "SELECT user_id FROM USERS WHERE rename_true_false=\"TRUE\" "
            f"AND server_id='{self.guild.id}'"
        )
        return [item[0] for item in val] if type(val) is tuple else [val] if val != [] else []
    @property
    async def ymca_green_book_channel(self) -> discord.TextChannel|None:
        val = await ago.execute(
            "SELECT ymca_green_book_channel FROM SERVERS WHERE "
            f"server_id='{self.guild.id}'"
        )
        if val == [] or val is None: return None
        return self.guild.get_channel(int(val))
    @property
    async def ymca_supplies_channel(self) -> discord.TextChannel|None:
        val = await ago.execute(
            "SELECT ymca_supplies_channel FROM SERVERS WHERE "
            f"server_id='{self.guild.id}'"
        )
        if val == [] or val is None: return None
        return self.guild.get_channel(int(val))
    
    
    async def checklists(self, include_hidden: bool = False) -> list[Checklist]:
        val = await ago.execute(
            "SELECT checklist_id FROM CHECKLISTS WHERE "
            f"server_id='{self.guild.id}' "
            "ORDER BY pos ASC "
            f"LIMIT {tunables('MAX_ITEMS_PER_CHECKLIST')}"
        )
        if val is None or val == []: return []
        
        if type(val) == str:
            c = Checklist(id=val, emoji="1️⃣")
            await c.ainit()
            return [c] if c.visible or include_hidden else []
        
        temp = []
        i = 0
        for cid in val:
            c = Checklist(id=cid[0], emoji=emojis_1to10(i))
            await c.ainit()
            if c.visible or include_hidden:
                temp.append(c)
                i += 1
            
        return temp


    async def set_member_numbers(self) -> None:
        member_ids = await ago.execute(
            "SELECT user_id FROM USERS WHERE "
            f"server_id='{self.guild.id}' "
            "ORDER BY original_join_time ASC"
        )
        for i, db_member in enumerate(member_ids):
            await ago.execute(
                f"UPDATE USERS SET unique_number='{i+1}' WHERE "
                f"user_id='{db_member[0]}' AND server_id='{self.guild.id}'"
            )

    async def daily_msg_increment_guild(self) -> None:
        upd_cmd = []
        upd_cmd.append("UPDATE SERVERS SET ")

        # Using this logic, 'last_updated' will only be updated when a user
        # sends a message in a guild for the first time that day. And again
        # when a message is sent on a following day
        if await self.__last_updated >= today():
            upd_cmd.append(f"messages_today='{await self.guild_messages_today + 1}'")
        else:
            upd_cmd.append(f"messages_today='{await self.guild_messages_today + 1}',last_updated='{int(time.time())}'")

        upd_cmd.append(f" WHERE server_id={self.guild.id}")
        await ago.execute(''.join(upd_cmd))
        return
    
    async def __leave_guild_log_message(self) -> None:

        i = 0
        while self.log_channel is None:
            await asyncio.sleep(1)
            if i >= 10:
                print("Log channel not found")
                return
            i += 1

        await self.log_channel.send(
            content=(
                "```diff\n"
                "- I left a guild! -\n"
                "```\n"
                f"> Left: <t:{int(time.time())}:R>\n"
                f"> Guild name: **{self.guild.name}** [`{self.guild.id}`]\n"
                f"> Guild owner: {self.guild.owner.mention} [`{self.guild.owner.id}`] 『`{self.guild.owner}`』\n"
                f"> Guild members: `{self.guild.member_count}`\n"
                f"> Guild profile [DB]: `{await self.status}`\n"
                f"> Guild Locale (Region): `{self.guild.preferred_locale}`\n"
                f"> Guild 2FA Level: `{self.guild.mfa_level}`\n"
                f"> Guild NSFW Level: `{self.guild.nsfw_level}`\n"
                f"> Guild Nitro boost level: `{self.guild.premium_tier}`\n"
                f"> Guild Nitro boost count: `{self.guild.premium_subscription_count}`\n"
                f"> Guild Text Channels: `{len(self.guild.text_channels) if self.guild.text_channels is not None else 0}`\n"
                f"> Guild Voice Channels: `{len(self.guild.voice_channels) if self.guild.voice_channels is not None else 0}`\n"
                f"> Guild Vanity URL: {self.guild.vanity_url} | `{self.guild.vanity_url_code}`\n"
                f"> Guild Icon: {self.guild.icon}\n"
                f"> Guild Banner: {self.guild.banner}\n"
            ),
            allowed_mentions=discord.AllowedMentions(users=False)
        )

    async def __new_guild_log_message(self, new=True) -> None:

        channel = None
        if self.guild.system_channel is not None: channel = self.guild.system_channel
        else:
            for ch in self.guild.text_channels:
                channel = ch
                if ch.permissions_for(self.guild.me).send_messages: break
        
        if channel is not None:
            try:
                sent_channel = f"**Yes**. To {channel.mention} [`{channel.id}`] 『`#{channel.name}`』"
                u = MikoMember(user=self.guild.owner, client=self.client, check_exists=False)
                embed=discord.Embed(
                    color=GLOBAL_EMBED_COLOR,
                    description=''.join(await help_embed(u=u))
                )
                embed.set_author(
                    icon_url=self.client.user.avatar,
                    name=f"{self.client.user.name} Help"
                )
                await channel.send(
                    content=(
                        "Thanks for adding me to your server! I have automatically enabled "
                        "playtime and voicetime tracking for all users in this guild. If you "
                        f"would like to change these settings, use {tunables('SLASH_COMMAND_SUGGEST_SETTINGS')}."
                    ),
                    embed=embed
                )
            except Exception as e: sent_channel = f"**No**: `{e}`"
        else: sent_channel = "**No**."

        i = 0
        while self.log_channel is None:
            await asyncio.sleep(1)
            if i >= 10: return
            i += 1

        await self.log_channel.send(
            content=(
                "```diff\n"
                f"+ I {'joined' if new else 'REJOINED'} a guild! +\n"
                "```\n"
                f"> Added: <t:{int(time.time())}:R>\n"
                f"> Help embed sent? {sent_channel}\n"
                f"> Guild name: **{self.guild.name}** [`{self.guild.id}`]\n"
                f"> Guild owner: {self.guild.owner.mention} [`{self.guild.owner.id}`] 『`{self.guild.owner}`』\n"
                f"> Guild members: `{self.guild.member_count}`\n"
                f"> Guild profile [DB]: `{await self.status}`\n"
                f"> Guild Locale (Region): `{self.guild.preferred_locale}`\n"
                f"> Guild 2FA Level: `{self.guild.mfa_level}`\n"
                f"> Guild NSFW Level: `{self.guild.nsfw_level}`\n"
                f"> Guild Nitro boost level: `{self.guild.premium_tier}`\n"
                f"> Guild Nitro boost count: `{self.guild.premium_subscription_count}`\n"
                f"> Guild Text Channels: `{len(self.guild.text_channels) if self.guild.text_channels is not None else 0}`\n"
                f"> Guild Voice Channels: `{len(self.guild.voice_channels) if self.guild.voice_channels is not None else 0}`\n"
                f"> Guild Vanity URL: {self.guild.vanity_url} | `{self.guild.vanity_url_code}`\n"
                f"> Guild Icon: {self.guild.icon}\n"
                f"> Guild Banner: {self.guild.banner}\n"
                f"> My permissions: `{self.guild.me.guild_permissions}`\n"
            ),
            allowed_mentions=discord.AllowedMentions(users=False)
        )

    async def handle_leave_guild(self) -> None:
        await self.__leave_guild_log_message()

    async def __handle_returning_guild(self) -> None:
        await self.__new_guild_log_message(new=False)

    async def __handle_new_guild(self) -> None:
        await self.__new_guild_log_message()

    async def __exists(self) -> None:
        sel_cmd = f"SELECT cached_name,owner_name,owner_id,total_members,latest_join_time FROM SERVERS WHERE server_id='{self.guild.id}'"
        rows = await ago.execute(sel_cmd)

        # If guild exists in database, update cache and return
        if ago.exists(len(rows)):
            await self.__update_cache(rows)
            return


        # If guild does not exist in database, create it
        ins_cmd = (
            "INSERT INTO SERVERS (server_id, latest_join_time, cached_name, owner_name, owner_id, total_members, status) VALUES "
            f"('{self.guild.id}', '{int(self.guild.me.joined_at.timestamp())}', '{sanitize_name(self.guild.name)}', '{sanitize_name(self.guild.owner.name)}', "
            f"'{self.guild.owner.id}', '{self.guild.member_count}', '{tunables('DEFAULT_GUILD_STATUS')}')"
        )
        await ago.execute(ins_cmd)
        await self.__handle_new_guild()
        print(f"Added server {self.guild.name} ({self.guild.id}) to database")
        await self.add_all_members()

    async def add_all_members(self) -> None:
        for member in self.guild.members:
            u = MikoMember(user=member, client=self.client, check_exists_guild=False)
            await u.ainit()
        await self.set_member_numbers()

    async def __update_cache(self, rows) -> None:
        params_temp = []
        params_temp.append("UPDATE SERVERS SET ")

        updating = False
        if self.guild.name != rows[0][0]:
            updating = True
            params_temp.append(f"cached_name='{sanitize_name(self.guild.name)}'")
        
        if str(self.guild.owner) != rows[0][1]:
            if updating: params_temp.append(",")
            updating = True
            params_temp.append(f"owner_name='{sanitize_name(self.guild.owner)}'")
        
        if self.guild.owner.id != rows[0][2]:
            if updating: params_temp.append(",")
            updating = True
            params_temp.append(f"owner_id=\"{self.guild.owner.id}\"")

        if self.guild.member_count != rows[0][3]:
            if updating: params_temp.append(",")
            updating = True
            params_temp.append(f"total_members=\"{self.guild.member_count}\"")

        latest_join_time = int(self.guild.me.joined_at.timestamp())
        if latest_join_time != rows[0][4]:
           if updating: params_temp.append(",")
           updating = True
           params_temp.append(f"latest_join_time='{latest_join_time}'")
           if rows[0][4] != 0 and type(rows[0][4] == int): await self.__handle_returning_guild()
        
        if updating:
            params_temp.append(f" WHERE server_id=\"{self.guild.id}\"")
            upd_cmd = f"{''.join(params_temp)}"
            await ago.execute(upd_cmd)
        return


class MikoTextChannel(MikoGuild):

    def __init__(self, channel: discord.TextChannel, client: discord.Client):
        super().__init__(guild=channel.guild, client=client)
        self.channel = channel

    async def ainit(self, check_exists: bool = True, check_exists_guild: bool = True, skip_if_locked: bool = False):
        if check_exists and \
            not (skip_if_locked and lock_status(key=self.channel.id)):
            async with check_lock(key=self.channel.id):
                await super().ainit(check_exists=check_exists_guild)
                await self.__exists()

    @property
    async def is_private(self) -> bool:
        sel_cmd = (
            "SELECT private_true_false FROM CHANNELS WHERE "
            f"channel_id='{self.channel.id}' AND server_id='{self.guild.id}'"
        )
        val = await ago.execute(sel_cmd)
        if val == [] or "FALSE": return True
        return False
    @property
    async def channel_messages(self):
        sel_cmd = (
            "SELECT SUM(count) FROM USER_MESSAGE_COUNT WHERE "
            f"channel_id='{self.channel.id}' AND server_id='{self.guild.id}'"
        )
        val = await ago.execute(sel_cmd)
        if val == [] or val is None: return 0
        return int(val)
    @property
    async def channel_messages_nobots(self):
        sel_cmd = (
            "SELECT SUM(mc.count) FROM USER_MESSAGE_COUNT AS mc "
            "INNER JOIN USERS AS u ON "
            "(mc.user_id=u.user_id AND mc.server_id=u.server_id AND u.is_bot!='TRUE') WHERE "
            f"mc.channel_id='{self.channel.id}' AND mc.server_id='{self.guild.id}'"
        )
        val = await ago.execute(sel_cmd)
        if val == [] or val is None: return 0
        return int(val)
    @property
    async def gpt_mode(self) -> str|None:
        val = await ago.execute(
            "SELECT chatgpt FROM CHANNELS WHERE "
            f"channel_id='{self.channel.id}'"
        )
        if val is None or val in [[], "DISABLED"]: return None
        return val
    @property
    async def gpt_personality(self) -> str|None:
        mode = await self.gpt_mode
        if mode is None: return None
        
        role = tunables(f'OPENAI_PERSONALITY_{mode}')
        if role is None:
            await self.set_gpt_mode(mode="DISABLED")
            return
        
        return role
    @property
    async def gpt_threads(self) -> str|None:
        val = await ago.execute(
            "SELECT chatgpt_threads FROM CHANNELS WHERE "
            f"channel_id='{self.channel.id}'"
        )
        if val is None or val in [[], "DISABLED"]: return None
        return val
        
    async def set_gpt_mode(self, mode: str) -> None:
        await ago.execute(
            f"UPDATE CHANNELS SET chatgpt='{mode}' WHERE "
            f"channel_id='{self.channel.id}'"
        )

    async def __exists(self) -> None:
        sel_cmd = f"SELECT * FROM CHANNELS WHERE server_id='{self.guild.id}' AND channel_id='{self.channel.id}'"
        rows = await ago.execute(sel_cmd)

        # If channel exists in database, update cache and return
        if ago.exists(len(rows)):
            await self.__update_cache(rows)
            return
        
        # If channel does not exist, create it
        ins_cmd = (
            "INSERT INTO CHANNELS (server_id,channel_id,channel_name,created_at) VALUES "
            f"('{self.guild.id}', '{self.channel.id}', '{sanitize_name(self.channel.name)}', "
            f"'{int(self.channel.created_at.timestamp())}')"
        )
        await ago.execute(ins_cmd)
        print(f"Added channel {self.channel.name} ({self.channel.id}) from {self.guild.name} ({self.guild.id}) to database")
    
    async def __update_cache(self, rows) -> None:
        params_temp = []
        params_temp.append("UPDATE CHANNELS SET ")

        overwrite = self.channel.overwrites_for(self.channel.guild.default_role)
        if overwrite.view_channel == False:
            # Tell our database this channel is PRIVATE
            is_private = "TRUE"
        else:
            # Tell our database this channel is PUBLIC
            is_private = "FALSE"

        updating = False
        if self.channel.name != rows[0][0]:
            updating = True
            params_temp.append(f"channel_name='{sanitize_name(self.channel.name)}'")
        
        if is_private != rows[0][1]:
            if updating: params_temp.append(",")
            updating = True
            params_temp.append(f"private_true_false=\"{is_private}\"")
        
        if updating:
            params_temp.append(f" WHERE server_id=\"{self.guild.id}\" AND channel_id=\"{self.channel.id}\"")
            upd_cmd = f"{''.join(params_temp)}"
            await ago.execute(upd_cmd)
        return

    

class MikoMember(MikoGuild):
    def __init__(self, user: discord.Member, client: discord.Client, guild_id: int = None, check_exists=True, check_exists_guild=True):
        if guild_id is None: super().__init__(guild=user.guild, client=client, check_exists=check_exists, check_exists_guild=check_exists_guild)
        else: super().__init__(guild=None, client=client, guild_id=guild_id, check_exists=check_exists, check_exists_guild=check_exists_guild)
        self.user = user
    
    async def ainit(self, check_exists: bool = True, check_exists_guild: bool = True, skip_if_locked: bool = False):
        if (check_exists and not (self.user.pending and (await self.profile).feature_enabled('SKIP_VERIFICATION') != 1)) and \
            not (skip_if_locked and lock_status(key=self.user.id)):
            async with check_lock(key=self.user.id):
                await self.__exists()
                await super().ainit(check_exists=check_exists_guild)

    def __str__(self):
        return f"{self.user} - {self.guild} | MikoMember Object"

    @property
    async def __last_updated(self) -> int:
        val = await ago.execute(
            "SELECT last_updated FROM USERS WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        if val is not None and val != []: return int(val)
        print(f"Error when checking 'last_updated' in MikoMember object: {val} | {self.user} | {self.user.id} | {self.guild} | {self.guild.id} | {int(time.time())}")
        return 1
    @property
    async def first_joined(self) -> int:
        val = await ago.execute(
            "SELECT original_join_time FROM USERS WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        if val == [] or val is None: return -1
        return int(val)
    @property
    async def member_number(self) -> int:
        val = await ago.execute(
            "SELECT unique_number FROM USERS WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        if val == [] or val is None: return -1
        return int(val)
    @property
    async def user_voicetime(self) -> int:
        val = await ago.execute(
            "SELECT SUM(end_time - start_time) FROM VOICE_HISTORY WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}' AND end_time is not NULL AND "
            f"(end_time - start_time)>={tunables('THRESHOLD_LIST_VOICE_ACTIVITY')} GROUP BY user_id"
        )
        if val == [] or val is None: return 0
        return int(val)
    @property
    async def user_messages(self) -> int:
        val = await ago.execute(
            "SELECT SUM(count) FROM USER_MESSAGE_COUNT WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        if val == [] or val is None: return 0
        return int(val)
    @property
    async def user_messages_today(self) -> int:
        val = await ago.execute(
            "SELECT messages_today FROM USERS WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        if val == [] or val is None: return 0
        if await self.__last_updated >= today(): return int(val)
        return 0
    @property
    async def considered_bot(self) -> bool:
        val = await ago.execute(
            "SELECT is_bot FROM USERS WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        if val == [] or val is None or val == "FALSE": return False
        return True
    @property
    async def react(self) -> bool:
        val = await ago.execute(
            "SELECT react_true_false FROM USERS WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        if val == [] or val is None or val == "FALSE": return False
        return True
    @property
    async def reactall(self) -> bool:
        val = await ago.execute(
            "SELECT react_all_true_false FROM USERS WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        if val == [] or val is None or val == "FALSE": return False
        return True
    @property
    async def rename(self) -> bool:
        val = await ago.execute(
            "SELECT rename_true_false FROM USERS WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        if val == [] or val is None or val == "FALSE": return False
        return True
    @property
    async def renameany(self) -> bool:
        val = await ago.execute(
            "SELECT rename_any_true_false FROM USERS WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        if val == [] or val is None or val == "FALSE": return False
        return True
    @property
    async def usernames(self):
        val = await ago.execute(
            f"SELECT name,last_change FROM USERNAME_HISTORY WHERE "
            f"user_id={self.user.id} ORDER BY last_change DESC"
        )
        names = []
        for item in val:
            names.append(item[0])
            names.append(item[1])
        return names
    @property
    async def message_rank(self):
        val = await ago.execute(
            "SELECT row FROM ("
            "SELECT grouped.*, ROW_NUMBER() OVER ("
            "PARTITION BY grouped.server_id ORDER BY grouped.cnt DESC) AS row "
            "FROM ("
            "SELECT mc.server_id, mc.user_id, SUM(mc.count) AS cnt "
            "FROM USER_MESSAGE_COUNT AS mc "
            "INNER JOIN USERS AS u ON u.user_id=mc.user_id AND mc.server_id=u.server_id AND u.is_bot!='TRUE' "
            f"WHERE mc.server_id='{self.guild.id}' "
            "GROUP BY mc.user_id, mc.server_id) AS grouped) AS ranked "
            f"WHERE user_id='{self.user.id}' "
            "LIMIT 1"
        )
        if val == [] or val is None: return -1
        return int(val)
    # @property
    # def tokens(self) -> Token:
    #     return Token(user=self.user, guild=self.guild)
    @property
    def leveling(self) -> LevelClass:
        return LevelClass(u=self)
    # @property
    # def pets(self) -> PetOwner:
    #     return PetOwner(user=self.user)
    @property
    def playtime(self) -> Playtime:
        return Playtime(u=self)
    @property
    async def bot_permission_level(self):
        val = await ago.execute(
            "SELECT bot_permission_level FROM USERS WHERE "
            f"user_id='{self.user.id}' "
            "ORDER BY bot_permission_level DESC LIMIT 1"
        )
        if val == [] or val is None: return 0
        return int(val)
    @property
    async def do_big_emojis(self):
        val = await ago.execute(
            "SELECT big_emojis FROM USER_SETTINGS WHERE "
            f"user_id='{self.user.id}'"
        )
        if (await self.profile).feature_enabled('BIG_EMOJIS') != 1: return False
        if val == "FALSE" or not await self.guild_do_big_emojis: return False
        return True
    @property
    async def track_playtime(self):
        val = await ago.execute(
            "SELECT track_playtime FROM USER_SETTINGS WHERE "
            f"user_id='{self.user.id}'"
        )
        if val == "FALSE" or not tunables('FEATURE_ENABLED_TRACK_PLAYTIME'): return False
        return True
    @property
    async def public_playtime(self):
        val = await ago.execute(
            "SELECT public_playtime FROM USER_SETTINGS WHERE "
            f"user_id='{self.user.id}'"
        )
        if val == "FALSE": return False
        return True
    @property
    async def track_voicetime(self):
        val = await ago.execute(
            "SELECT track_voicetime FROM USER_SETTINGS WHERE "
            f"user_id='{self.user.id}'"
        )
        if val == "FALSE" or not tunables('FEATURE_ENABLED_TRACK_VOICETIME'): return False
        return True
    @property
    async def public_voicetime(self):
        val = await ago.execute(
            "SELECT public_voicetime FROM USER_SETTINGS WHERE "
            f"user_id='{self.user.id}'"
        )
        if val == "FALSE": return False
        return True

    '''
    user_avatar
        Will return guild avatar (if enabled by guild) if there is one
        or will return user avatar
    username
        Will return guild nickname (if enabled by guild) if there is one
        or will return user name (without discriminator)
    '''
    @property
    async def user_avatar(self):
        if self.user.guild_avatar is None: return self.user.avatar
        elif await self.nickname_in_ctx: return self.user.guild_avatar
        return self.user.avatar
    @property
    async def username(self):
        if self.user.nick is None: return self.user.name
        elif await self.nickname_in_ctx: return self.user.nick
        return self.user.name
    @property
    async def manage_guild(self):
        perms = self.user.guild_permissions
        if perms.administrator: return True
        if perms.manage_guild: return True
        if await self.bot_permission_level >= 5: return True
        return False
    

    # async def __member_leave_message(self) -> None: pass

    async def __new_member_greeting(self, new=True) -> None:
        match await self.status:

            case "THEBOYS":

                if self.client.user.id != 1017998983886545068: return # Only send welcome messages/role assignments if prod miko
                channel = self.guild.system_channel
                if channel is not None:
                    await asyncio.sleep(1) # To ensure welcome message is sent after join message
                    await channel.send(
                        content=(
                            f'Hi {self.user.mention}, welcome{" BACK" if not new else ""} to {self.guild}! :tada:\n'
                            f'> You are unique member `#{await self.member_number}`'
                        ), silent=True
                    )
                else: print(f"\n\n**************************\nCOULD NOT SEND WELCOME MESSAGE FOR {self.user}\n**************************\n\n")
                
                '''
                As of 12/11/2022, we will no longer assign the 'OG Bro'
                role to new users at join. [theboyshangout]
                '''

                holiday = self.guild.get_role(get_holiday(self.user, "ROLE"))
                await self.user.add_roles(holiday)
                
                if self.user.bot:
                    bot = self.guild.get_role(890642126445084702)
                    await self.user.add_roles(bot)
                    return

                leveling_role = await self.leveling.get_role()
                await self.user.add_roles(leveling_role)
            
            case "YMCA":

                # Log channel [temporary, ensure skipping verification]
                try:
                    if self.guild.id != 1060357911483797704 or not self.user.pending: raise Exception
                    channel = self.guild.get_channel(1060371116310401034)
                    await channel.send(
                        content=f"Bypassing Community Verification for {self.user.mention}",
                        allowed_mentions=discord.AllowedMentions(users=False),
                        silent=True
                    )
                except: pass

                lifeguard = discord.utils.get(self.guild.roles, name="Lifeguard")
                if not self.user.bot: await self.user.add_roles(lifeguard)
            
            case "DEBUG":
                channel = self.guild.system_channel
                if channel is not None:
                    await channel.send(
                        content=(
                            f"Welcome {self.user} {await self.member_number}"
                        ), silent=True
                    )

    # async def handle_member_leave(self) -> None: pass

    async def __handle_new_member(self) -> None:
        if self.user.id == self.client.user.id or \
            (await self.profile).feature_enabled('GREET_NEW_MEMBERS') != 1: return
        await self.__new_member_greeting()
    
    async def __handle_returning_member(self) -> None:
        if self.user.id == self.client.user.id or \
            (await self.profile).feature_enabled('GREET_NEW_MEMBERS') != 1: return
        await self.__new_member_greeting(new=False)


    async def __exists(self) -> None:
        sel_cmd = f"SELECT cached_username,latest_join_time FROM USERS WHERE user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        rows = await ago.execute(sel_cmd)
        await self.__settings_exist()

        if ago.exists(len(rows)):
            await self.__update_cache(rows)
            return
        

        latest_join_time = int(self.user.joined_at.timestamp())
        ins_cmd = (
            "INSERT INTO USERS (server_id,user_id,original_join_time,latest_join_time,cached_username) VALUES "
            f"('{self.guild.id}', '{self.user.id}', '{latest_join_time}', '{latest_join_time}',"
            f"\"{self.user}\")"
        )
        await ago.execute(ins_cmd)
        print(f"Added user {self.user.id} ({self.user}) in guild {self.guild} ({self.guild.id}) to database")


        # Unique number handling
        val = await ago.execute(
            "SELECT unique_number FROM USERS WHERE "
            f"server_id='{self.guild.id}' ORDER BY unique_number DESC LIMIT 1"
        )
        if val == [] or val is None: return
        await ago.execute(
            f"UPDATE USERS SET unique_number={int(val)+1} WHERE user_id='{self.user.id}' "
            f"AND server_id='{self.guild.id}'"
        )
        
        await self.__handle_new_member() # new member
    
    async def __settings_exist(self):
        rows = await ago.execute(f"SELECT * FROM USER_SETTINGS WHERE user_id='{self.user.id}'")
        if ago.exists(len(rows)): return
        await ago.execute(
            f"INSERT INTO USER_SETTINGS (user_id) VALUES ('{self.user.id}')"
        )

    async def __username_history(self, old_name: str) -> None:
        names_len = len(await self.usernames)
        
        for i in [0,1]:
            if names_len != 0 and i > 0: break
            await ago.execute(
                "INSERT INTO USERNAME_HISTORY (user_id,name,last_change) VALUES "
                f"('{self.user.id}', '{sanitize_name(old_name) if names_len+i == 0 and i == 0 else sanitize_name(self.user)}', "
                f"{int(self.user.created_at.timestamp()) if names_len+i == 0 and i == 0 else int(time.time())})"
            )
        
        await ago.execute(
            f"UPDATE USERS SET cached_username='{sanitize_name(self.user)}' WHERE "
            f"user_id='{self.user.id}'"
        )

    async def __update_cache(self, rows) -> None:
        params_temp = []
        params_temp.append("UPDATE USERS SET ")

        updating = False
        if str(self.user) != rows[0][0]:
            await self.__username_history(old_name=rows[0][0])

        latest_join_time = int(self.user.joined_at.timestamp())
        if latest_join_time != rows[0][1]:
           if updating: params_temp.append(",")
           updating = True
           params_temp.append(f"latest_join_time='{latest_join_time}'")
           if rows[0][1] != 0 and type(rows[0][1] == int): await self.__handle_returning_member() # returning member
        
        if updating:
            params_temp.append(f" WHERE user_id=\"{self.user.id}\" AND server_id=\"{self.guild.id}\"")
            upd_cmd = f"{''.join(params_temp)}"
            await ago.execute(upd_cmd)
    
    async def add_rename_hell(self) -> bool:
        val = await ago.execute(
            "SELECT rename_any_true_false FROM USERS WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        if val == "TRUE": return False

        await ago.execute(
            "UPDATE USERS SET rename_any_true_false=\"TRUE\" WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        return True

    async def del_rename_hell(self) -> bool:
        val = await ago.execute(
            "SELECT rename_any_true_false FROM USERS WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        if val == "FALSE" or val == "": return False

        await ago.execute(
            "UPDATE USERS SET rename_any_true_false=\"FALSE\" WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        return True
    
    async def manage_channel(self, channel: discord.TextChannel) -> bool:
        manage_channels = channel.permissions_for(self.user).manage_channels
        if manage_channels: return True
        if await self.bot_permission_level >= 5: return True
        return False
    
    async def daily_msg_increment_user(self) -> None:
        await self.daily_msg_increment_guild()
        upd_cmd = []
        upd_cmd.append("UPDATE USERS SET ")

        # Using this logic, 'last_updated' will only be updated when a user
        # sends a message in a guild for the first time that day. And again
        # when a message is sent on a following day
        if await self.__last_updated >= today():
            upd_cmd.append(f"messages_today='{await self.user_messages_today + 1}'")
        else:
            upd_cmd.append(f"messages_today='{await self.user_messages_today + 1}',last_updated='{int(time.time())}'")

        upd_cmd.append(f" WHERE server_id={self.guild.id} AND user_id='{self.user.id}'")
        await ago.execute(''.join(upd_cmd))
        return
    
    async def increment_statistic(self, key: str, increment: int=1) -> None:
        key = key.upper()
        val = await ago.execute(
            "SELECT value FROM STATISTICS WHERE "
            f"server_id='{self.guild.id}' AND user_id='{self.user.id}' "
            f"AND stat=\"{key}\" LIMIT 1"
        )
        if val is None or val == []:
            await ago.execute(
                "INSERT INTO STATISTICS (server_id,user_id,stat,value) VALUES "
                f"('{self.guild.id}', '{self.user.id}', '{key}', '{increment}')"
            )
            return
        
        await ago.execute(
            f"UPDATE STATISTICS SET value='{val + increment}' WHERE "
            f"server_id='{self.guild.id}' AND user_id='{self.user.id}' AND "
            f"stat='{key}'"
        )

    async def get_statistic(self, key: str) -> int:
        val = await ago.execute(
            "SELECT value FROM STATISTICS WHERE "
            f"server_id='{self.guild.id}' AND user_id='{self.user.id}' "
            f"AND stat='{key}' LIMIT 1"
        )
        if val is None or val == []: return 0
        return int(val)
        
class RawMessageUpdate():
    def __init__(self, payload: discord.RawMessageUpdateEvent) -> None:
        self.payload = payload
    
    async def __get_attachments(self) -> str:
        if len(self.payload.data['attachments']) > 0:
            for attachment in self.payload.data['attachments']:
                if attachment['filename'] != "message.txt": continue
                async with aiohttp.ClientSession() as ses:
                    async with ses.get(attachment['url']) as r:
                        if r.status in range(200, 299):
                            data = BytesIO(await r.read())
                            try: data = data.getvalue().decode()
                            except: return []
                            return data
        return []
    
    async def ainit(self) -> None:
        if not tunables('MESSAGE_CACHING'): return
        m = await r.get(key=f"m:{self.payload.message_id}", type="JSON")
        if m is None: return
        
        # Update message content
        await r.set(
            key=f"m:{self.payload.message_id}",
            type="JSON",
            path="$.content",
            value=self.payload.data['content']
        )
        
        # Update attachments
        data = await self.__get_attachments()
        await r.set(
            key=f"m:{self.payload.message_id}",
            type="JSON",
            path="$.attachments",
            value=[{
                'filename': "message.txt",
                'data': data
            }] if data != [] else []
        )
        
        # Update embed description
        embeds = []
        if len(self.payload.data['embeds']) > 0:
            for embed in self.payload.data['embeds']:
                if embed['description'] is None or embed['description'] == "": continue
                embeds.append({
                    'description': embed['description']
                })
        await r.set(
            key=f"m:{self.payload.message_id}",
            type="JSON",
            path="$.embeds",
            value=embeds
        )

class CachedMessage:
    def __init__(self, message_id: int=None, m: dict=None) -> None:
        self.message_id = message_id
        self.m = m
        self.id: int = None
        self.content: str = None
        self.embeds = []
        self.author: CachedUser = None
        self.thread: CachedChannel = None
        self.channel: CachedChannel = None
        self.guild: CachedGuild = None
        self.reference: CachedReference = None
        self.attachments = []
        if m is not None:
            try: self.__assign_attributes()
            except Exception as e: print(f"Cached error {e}")
    
    async def ainit(self):
        if not tunables('MESSAGE_CACHING'): return
        self.m = await r.get(key=f"m:{self.message_id}", type="JSON")
        if self.m is None: return
        self.__assign_attributes()
    
    def __assign_attributes(self):
        self.id = int(self.m['id'])
        self.content = self.m['content']
        self.author = CachedUser(name=self.m['author']['name'], id=int(self.m['author']['id']))
        self.created_at = self.m['created_at']
        for embed in self.m['embeds']:
            self.embeds.append(
                CachedEmbed(embed=embed)
            )
        if self.m['reference_id'] is not None and self.m['reference_id'] != "null":
            self.reference = CachedReference(message_id=int(self.m['reference_id']))
        for attachment in self.m['attachments']:
            self.attachments.append(
                CachedAttachment(attachment=attachment)
            )
        if self.m['thread'] is not None and self.m['thread'] != "null":
            self.thread = CachedChannel(
                name=self.m['thread']['name'],
                type=self.m['thread']['type'],
                id=self.m['thread']['id']
            )
        self.channel = CachedChannel(
            name=self.m['channel']['name'],
            type=self.m['channel']['type'],
            id=self.m['channel']['id']
        )
        self.guild = CachedGuild(
            name=self.m['guild']['name'],
            id=self.m['guild']['id'],
            owner=CachedUser(name=self.m['guild']['owner']['name'], id=int(self.m['guild']['owner']['id']))
        )
    
    
class CachedUser:
    def __init__(self, name: str, id: int):
        self.name=name
        self.id=id
        self.mention = f"<@{id}>"
    def __str__(self) -> str: return self.name

class CachedChannel:
    def __init__(self, name: str, type: str, id: int):
        self.name=name,
        self.type=type,
        self.id=id
    def __str__(self) -> str: return self.name

class CachedGuild:
    def __init__(self, name: str, id: int, owner: CachedUser):
        self.name=name
        self.id=id
        self.owner = owner
    def __str__(self) -> str: return self.name

class CachedReference:
    def __init__(self, message_id: int) -> None:
        self.message_id=message_id
        self.cached_message = None

class CachedEmbed:
    def __init__(self, embed: dict) -> None:
        self.description = embed['description']

class CachedAttachment:
    def __init__(self, attachment: dict):
        self.data = attachment['data']
        self.filename = attachment['filename']
        

class MikoMessage():
    def __init__(self, message: discord.Message, client: discord.Client):
        self.user = MikoMember(user=message.author, client=client)
        
        self.t = discord.ChannelType
        self.threads = [self.t.public_thread, self.t.private_thread, self.t.news_thread]
        match message.channel.type:
            case self.t.text | self.t.voice | self.t.news | self.t.forum | self.t.stage_voice:
                self.channel = MikoTextChannel(channel=message.channel, client=client)
            
            case self.t.public_thread | self.t.private_thread | self.t.news_thread:
                self.channel = MikoTextChannel(channel=message.channel.parent, client=client)
            
            case _: return
        
        self.message = message
    
    async def ainit(self, check_exists=True):
        await self.__cache_message()
        # No lock because messages are unique
        if check_exists:
            await self.user.ainit()
            await self.channel.ainit(check_exists_guild=False)
            await self.__exists()
    
    async def __cache_message(self) -> None:
        if not tunables('MESSAGE_CACHING'): return
        
        m = await r.get(key=f"m:{self.message.id}", type="JSON")
        if m is None:
            
            embeds = []
            if len(self.message.embeds) > 0:
                for embed in self.message.embeds:
                    if embed.description is None or embed.description == "": continue
                    embeds.append({
                        'description': embed.description
                    })
            
            attachments = []
            if len(self.message.attachments) > 0 and self.message.attachments[0].filename == "message.txt":
                try:
                    attachments.append({
                        'filename': "message.txt",
                        'data': (await self.message.attachments[0].read()).decode()
                    })
                except: pass
            
            await r.set(
                key=f"m:{self.message.id}",
                type="JSON",
                value={
                    'id': str(self.message.id),
                    'content': self.message.content,
                    'created_at': int(self.message.created_at.timestamp()),
                    'reference_id': None if self.message.reference is None else str(self.message.reference.message_id),
                    'attachments': attachments,
                    'embeds': embeds,
                    'author': {
                        'name': str(self.message.author),
                        'id': str(self.message.author.id)
                    },
                    'thread': None if self.message.channel.type not in self.threads else {
                        'name': str(self.message.channel.name),
                        'type': str(self.message.channel.type),
                        'id': str(self.message.channel.id),
                    },
                    'channel': {
                        'name': str(self.message.channel.name),
                        'type': str(self.message.channel.type),
                        'id': str(self.message.channel.id)
                    } if self.message.channel.type not in self.threads else {
                        'name': str(self.message.channel.parent.name),
                        'type': str(self.message.channel.parent.type),
                        'id': str(self.message.channel.parent_id)
                    },
                    'guild': {
                        'name': str(self.message.guild),
                        'id': str(self.message.guild.id),
                        'owner': {
                            'name': str(self.message.guild.owner),
                            'id': str(self.message.guild.owner.id)
                        }
                    }
                }
            )
        else: pass # update cache?
    
    async def __exists(self) -> None:
        row = await ago.execute(
            "SELECT count FROM USER_MESSAGE_COUNT WHERE "
            f"user_id={self.user.user.id} AND channel_id={self.channel.channel.id} "
            f"AND server_id={self.user.guild.id}"
        )
        if type(row) is int or ago.exists(len(row)):
            self.__cached_count = int(row)
            await self.__increment_msg_count()
            return
        self.__cached_count = 1

        await ago.execute(
            "INSERT INTO USER_MESSAGE_COUNT (user_id,channel_id,server_id,count) VALUES "
            f"('{self.user.user.id}', '{self.channel.channel.id}', '{self.user.guild.id}', '1')"
        )
        print(f"Added user_message_count for {self.user.user} ({self.user.user.id}) in channel {self.channel.channel} ({self.channel.channel.id}) in server {self.user.guild} ({self.user.guild.id}) to database")
    
    async def __increment_msg_count(self) -> None:
        # Increment USER_MESSAGE_COUNT
        await ago.execute(
            f"UPDATE USER_MESSAGE_COUNT SET count='{self.__cached_count + 1}' WHERE "
            f"user_id={self.user.user.id} AND channel_id={self.channel.channel.id} AND server_id={self.user.guild.id}"
        )

        # Increment messages_today [MEMBER, GUILD]
        await self.user.daily_msg_increment_user()
    
    async def handle_leveling(self) -> None:
        if self.user.client.user.id != 1017998983886545068: return
        if not self.message.author.bot and (await self.channel.profile).feature_enabled('LEVELING') == 1:
            lc = self.user.leveling
            await lc.determine_xp_gained_msg()
            # tc = mm.user.tokens
            # tc.determine_tokens_gained_msg()
    
    async def handle_persistent_player_reposition(self) -> None:
        # Persistent music player embed. Will delete the embed and re-send
        # it so the embed is always the first message in the channel.
        try: sesh = AUDIO_SESSIONS[self.message.guild.id]
        except: sesh = None
        if sesh is not None and (await self.channel.music_channel).id == self.message.channel.id:
            # If message is not from miko OR if message IS from miko AND is not an embed, reposition
            if self.message.author != self.user.client.user or (self.message.embeds == [] and self.message.author == self.user.client.user):
                await sesh.reposition()
    
    def __should_interact(self) -> bool:
        return self.message.channel.type not in self.threads
    
    async def handle_rename_hell(self) -> None:
        if await self.channel.guild_messages % 20 == 0 and self.message.channel.id != 963928489248063539:
            users = await self.user.renamehell_members
            if users != [] and users is not None:
                await self.message.add_reaction('<:nametag:1011514395630764032>')
                for user in users:
                    user = self.user.guild.get_member(int(user))
                    u = MikoMember(user=user, client=self.user.client)
                    try: await u.user.edit(nick=generate_nickname(self.message))
                    except discord.Forbidden as e:
                        await self.message.channel.send(f"Unable to rename {u.user.mention}, removing them from the renameany list: `{e}`")
                        await u.del_rename_hell()

    async def ugly_ass_sticker_removal(self) -> bool:
        if (await self.channel.profile).feature_enabled('UGLY_ASS_STICKER_REMOVAL') != 1\
            or self.channel.client.user.id != 1017998983886545068: return False
        try: l = tunables('UGLY_ASS_STICKERS').split(' ')
        except: l = [f'{tunables("UGLY_ASS_STICKERS")}']
        if self.message.stickers == []: return False
        if str(self.message.stickers[0].id) in l:
            await self.message.delete()
            try:
                d = datetime.datetime.now().astimezone()
                d += datetime.timedelta(minutes=1)
                await self.message.author.timeout(d, reason="Ugly ass fucking sticker")
            except: pass
            return True
        return False

    async def __big_emoji_embed(self, auth) -> discord.Embed:
        msg: discord.Message = self.message
        embed = discord.Embed(color=0x2f3136)
        embed.set_author(icon_url=await self.user.user_avatar, name=f'{sanitize_name(await self.user.username)}{"" if auth is None else f" → {auth}"}')
        url, emoji_name = get_emoji_url(msg.content)
        embed.set_image(url=url)
        embed.set_footer(text=f":{emoji_name}:")
        return embed

    async def handle_big_emojis(self) -> bool:
        if (not await self.user.do_big_emojis or self.message.author.bot) or \
            not self.__should_interact(): return False
        if len(self.message.content.split()) == 1 and self.message.author.id != self.user.client.user.id:
            if self.message.content.startswith("<") and self.message.content[1] not in ['@', '#']:
                try:
                    auth = None
                    if self.message.reference is not None:
                        ref = self.message.reference.resolved
                        if ref.author.id == self.user.client.user.id:
                            try:
                                embed = ref.embeds[0]
                                auth = embed.author.name.split("→")[0]
                            except: pass
                        else: auth = await MikoMember(user=ref.author, client=self.user.client).username

                    await self.message.delete()
                    e = await self.__big_emoji_embed(auth)
                    if auth is not None: await ref.reply(embed=e, silent=True)
                    else: await self.message.channel.send(embed=e, silent=True)
                    await self.user.increment_statistic('BIG_EMOJIS_SENT')
                    return True
                except Exception as e: print(f"Big emoji error: {e}")
        return False
    
    async def handle_bruh_react(self) -> None:
        if (await self.channel.profile).feature_enabled('BRUH_REACT') != 1 or self.user.client.user.id != 1017998983886545068: return
        for word in tunables('BRUH_REACT_WORDS').split():
            racist_regex =  rf".*\b{word}\b.*"
            if re.match(racist_regex, self.message.content.lower()) or word == self.message.content.lower():
                emoji = [
                    "\N{REGIONAL INDICATOR SYMBOL LETTER B}",
                    "\N{REGIONAL INDICATOR SYMBOL LETTER R}",
                    "\N{REGIONAL INDICATOR SYMBOL LETTER U}",
                    "\N{REGIONAL INDICATOR SYMBOL LETTER H}"
                ]
                for i, letter in enumerate(emoji):
                    if i > 0: await asyncio.sleep(0.5)
                    await self.message.add_reaction(letter)
                break
    
    async def handle_instagram_reel_links(self) -> bool:
        if (await self.channel.profile).feature_enabled('DELETE_INSTAGRAM_REEL_LINKS') != 1: return False
        ig_regex = r".*\binstagram.com\/reel\b.*"
        if re.match(ig_regex, self.message.content.lower()):
            await self.message.delete()
            return True
        return False
    
    async def handle_clown_react(self) -> None:
        if self.message.author.id in await self.channel.clown_react_users:
            await self.message.add_reaction('<:clown:903162517365330000>')
            
    async def handle_react_all(self) -> None:
        imgay = [
            "\N{REGIONAL INDICATOR SYMBOL LETTER I}",
            "\N{REGIONAL INDICATOR SYMBOL LETTER M}",
            "\N{LARGE BLUE SQUARE}",
            "\N{REGIONAL INDICATOR SYMBOL LETTER G}",
            "\N{REGIONAL INDICATOR SYMBOL LETTER A}",
            "\N{REGIONAL INDICATOR SYMBOL LETTER Y}"
        ]
        sample_list = random.sample(react_all_emoji_list(), 19)
        if self.message.author.id in await self.channel.react_all_users:
            num = random.randint(0, 10)
            if num == 5:
                for emoji in imgay:
                    await asyncio.sleep(0.5)
                    await self.message.add_reaction(emoji)
            else:
                for emoji in sample_list:
                    await asyncio.sleep(0.5)
                    await self.message.add_reaction(emoji)


# Placed here due to circular import
# Restore playtime sessions after reboot
async def fetch_playtime_sessions(client: discord.Client) -> None:
    
    end_time = await db.execute("SELECT value FROM PERSISTENT_VALUES WHERE variable='GLOBAL_REBOOT_TIME_ACTIVITY'")
    if end_time is None:
        end_time = await db.execute("SELECT end_time FROM PLAY_HISTORY WHERE end_time IS NOT NULL ORDER BY end_time DESC LIMIT 1")
    
    if end_time is None or end_time == []:
        print("Could not fetch a time to restore any playtime sessions.")
        return
    
    sel_cmd = (
        "SELECT user_id, session_id, app_id, start_time FROM PLAY_HISTORY "+
        f"WHERE end_time={end_time}"
    )
    val = list(await db.execute(sel_cmd))
    sessions_restored = 0
    
    # Not very fast, but only way to achieve game session restoration
    for guild in client.guilds:
        if val == []: break
        for member in guild.members:
            if val == []: break
            if val != [] and any(str(member.id) in sl for sl in val) and member.activities != ():
                
                b = copy.copy(member)
                b.activities = []
                app = PresenceUpdate(
                    u=MikoMember(user=member, client=client),
                    b=b, a=member, restored=True
                )
                await app.ainit()
                sessions_restored += 1
                print(f"> Restored {member}'s playtime session")

    if sessions_restored > 0:
        print(f"Restored {sessions_restored} playtime sessions.")
        print("Playtime session restoration complete.")
    else: print("No playtime sessions were restored.")