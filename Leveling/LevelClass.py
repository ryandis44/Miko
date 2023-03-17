import time
import discord
from Database.database import get_user_total_msgs_server
from Database.database_class import AsyncDatabase
from Voice.VoiceActivity import VoiceActivity, VOICE_SESSIONS
from tunables import *
from misc.misc import locate_htable_obj
# lc = Database("LevelClass.py")
alc = AsyncDatabase("LevelClass.py")

class LevelClass:


    def __init__(self, u):
        self.u = u
        self.user: discord.Member = u.user
        self.guild: discord.Guild = u.guild
    
    @property
    async def active_voicetime(self):
        current: VoiceActivity = locate_htable_obj(
            map=VOICE_SESSIONS,
            key=self.user.id
        )[0]
        if current is None: return 0
        return await current.time_elapsed
    @property
    async def xp(self) -> int:
        return await self.voice_xp + await self.msg_xp
    @property
    async def msgs(self):
        return await self.u.user_messages
    @property
    async def voice_xp(self) -> int:
        val = await alc.execute(
            "SELECT voice_xp FROM USERS WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        if val == [] or val is None: return 0
        return int(val)
    @property
    async def msg_xp(self) -> int:
        val = await alc.execute(
            "SELECT msg_xp FROM USERS WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        if val == [] or val is None: return 0
        return int(val)
    @property
    async def level(self) -> int:
        lv = 0
        xp = await self.xp
        if xp >= tunables('XP_LEVEL_01'): lv += 1
        if xp >= tunables('XP_LEVEL_02'): lv += 1
        if xp >= tunables('XP_LEVEL_03'): lv += 1
        if xp >= tunables('XP_LEVEL_04'): lv += 1
        if xp >= tunables('XP_LEVEL_05'): lv += 1
        if xp >= tunables('XP_LEVEL_06'): lv += 1
        if xp >= tunables('XP_LEVEL_07'): lv += 1
        if xp >= tunables('XP_LEVEL_08'): lv += 1
        if xp >= tunables('XP_LEVEL_09'): lv += 1
        if xp >= tunables('XP_LEVEL_10'): lv += 1
        return int(lv)
    
    async def determine_xp_gained_msg(self) -> None:
        if await self.msgs % tunables('THRESHOLD_MESSAGES_FOR_XP') != 0: return
        await self.add_xp_msg(tunables('XP_GAINED_FROM_MESSAGES'))
    
    async def determine_xp_gained_voice(self, sesh: VoiceActivity) -> None:
        if sesh.time_elapsed >= tunables('THRESHOLD_VOICETIME_FOR_XP') and sesh.time_elapsed % tunables('THRESHOLD_VOICETIME_FOR_XP') <= 90 and sesh.last_xp_award <= int(time.time() - 90):
            await self.add_xp_voice(tunables('XP_GAINED_FROM_VOICETIME'))
            sesh.last_xp_award = int(time.time())
    
    async def add_xp_msg(self, xp, manual=False) -> None:
        lv = await self.level
        upd_cmd = f"UPDATE USERS SET msg_xp={await self.msg_xp + xp} WHERE server_id='{self.guild.id}' AND user_id='{self.user.id}'"
        await alc.execute(upd_cmd)
        if await self.level > lv and not manual: await self.__assign_role()

    async def add_xp_voice(self, xp, manual=False) -> None:
        lv = await self.level
        upd_cmd = f"UPDATE USERS SET voice_xp={await self.voice_xp + xp} WHERE server_id='{self.guild.id}' AND user_id='{self.user.id}'"
        await alc.execute(upd_cmd)
        if await self.level > lv and not manual: await self.__assign_role()
    
    async def __assign_role(self) -> None:
        role = await self.get_role()
        leveling_roles = [
            self.guild.get_role(tunables('RANK_ID_LEVEL_01')),
            self.guild.get_role(tunables('RANK_ID_LEVEL_05')),
            self.guild.get_role(tunables('RANK_ID_LEVEL_10'))
        ]
        await self.user.remove_roles(*leveling_roles)
        await self.user.add_roles(role)
    
    async def __get_role_id(self) -> int:
        level = await self.level
        if level >= 10: return tunables('RANK_ID_LEVEL_10')
        elif level >= 5: return tunables('RANK_ID_LEVEL_05')
        else: return tunables('RANK_ID_LEVEL_01')
    
    async def get_role(self) -> discord.Role:
        id = await self.__get_role_id()
        return self.guild.get_role(id)