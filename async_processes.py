import time
import asyncio
import aiohttp
import discord
import threading
from Database.ApplicationObjects import Application
from Plex.background import end_of_week_int
from Plex.embeds import plex_multi_embed, plex_upcoming
from Presence.GameActivity import GameActivity
from Voice.VoiceActivity import VoiceActivity, VOICE_SESSIONS
from Database.GuildObjects import MikoMember, CHECK_LOCK
from Database.database_class import AsyncDatabase
from Polls.UI import active_polls
from Presence.Objects import PRESENCE_UPDATES, PLAYTIME_SESSIONS

from tunables import tunables
db = AsyncDatabase("async_processes.py")

client: discord.Client = None
def set_async_client(c):
    global client
    client = c


class MaintenanceThread(threading.Thread):
 
    def __init__(self, *args, **kwargs):
        super(MaintenanceThread, self).__init__(*args, **kwargs)
        self._stop = threading.Event()
 
    def stop(self):
        self._stop.set()
 
    def stopped(self):
        return self._stop.isSet()

    def run(self):
        num = -1
        while True:

            if num % 10 == 0:
                try:
                    for table in [PRESENCE_UPDATES, CHECK_LOCK]: lock_table_cleanup(table=table)
                except Exception as e: print(f"Presence table cleanup failed: {e}")
            
            if num >= 1000: num = 0
            num += 1
            time.sleep(1)

def lock_table_cleanup(table: dict) -> None:
        if len(table) == 0: return
        t = int(time.time())
        del_list = []
        for key, update in table.items():
            if update['at'] < t - 15:
                del_list.append(key)
        
        for key in del_list:
            del table[key]

async def heartbeat():
    num = 1
    while True:
        if num % 10 == 0:
            try: await voice_heartbeat()
            except Exception as e: print(f"some shit stopped working idk [voice heartbeat]: {e}")
            
        if num % 60 == 0:
            try: await check_notify()
            except Exception as e: print(f"Plex notify check failed, trying again in 60 seconds...: {e}")
            
            try: await playtime_heartbeat()
            except Exception as e: print(f"Playtime heartbeat failed: {e}")

        # Check if miko is still in guilds
        # if num % 3600 == 0:
        #     try:
        #     except Exception as e: print()

        if num == 3700: num = 0
        num += 1
        await asyncio.sleep(1)

    

async def voice_heartbeat(): # For leveling and tokens. The boys hangout only
    global client
    for key, session in VOICE_SESSIONS.items():
        session: VoiceActivity = session
        u = MikoMember(user=session.member, client=client)
        if (await u.profile).feature_enabled('VOICE_HEARTBEAT') != 1: return
        if client.user.id == 1017998983886545068:
            await u.leveling.determine_xp_gained_voice(sesh=session)
        # u.tokens.determine_tokens_gained_voice(sesh=session, voicetime=u.user_voicetime)

async def check_notify():
    if client.user.id != 1017998983886545068: return
    notify_time = await db.execute(
        "SELECT value FROM PERSISTENT_VALUES WHERE variable='PLEX_UPCOMING_NOTIFY'"
    )

    if notify_time is None or int(time.time()) >= notify_time:
        await db.execute(
            f"UPDATE PERSISTENT_VALUES SET value='{end_of_week_int()}' "
            f"WHERE variable='PLEX_UPCOMING_NOTIFY'"
        )

        url = await db.execute(
            "SELECT value_str FROM PERSISTENT_VALUES WHERE variable='PLEX_WEBHOOK_URL'"
        )
        embeds = plex_multi_embed()
        for i, embed in enumerate(embeds):
            async with aiohttp.ClientSession() as s:
                webhook = discord.Webhook.from_url(
                    url,
                    session=s
                )
                if i == 0:
                    try: await webhook.send(
                        embed=None,
                        content=tunables('PLEX_WEBHOOK_NOTIFICATION_MESSAGE')
                    )
                    except Exception as e: print(e)
                await asyncio.sleep(1)
                try: await webhook.send(
                    embed=embed,
                    content=None
                )
                except Exception as e: print(e)


async def playtime_heartbeat() -> None:
    if len(PLAYTIME_SESSIONS) == 0: return
    del_dict = {}
    users = PLAYTIME_SESSIONS.items()
    for user_sessions in users:
        for s in user_sessions[1]['sessions']:
            game: GameActivity = user_sessions[1]['sessions'][s]
            
            still_playing = False
            for activity in game.u.user.activities:
                activity: discord.Activity
                try:
                    if activity.type is discord.ActivityType.playing:
                        try: app_id = str(activity.application_id)
                        except: app_id = None
                        a = Application(
                            app={
                                'name': activity.name,
                                'app_id': app_id
                            }
                        )
                        await a.ainit()
                        
                        if a == game.app:
                            still_playing = True
                            break
                except: pass
            
            if not still_playing:
                val = del_dict.get(game.u.user.id)
                if val is None:
                    del_dict[game.u.user.id] = [game]
                else: val.append(game)
                
    
    for user_id, sessions in del_dict.items():
        for session in sessions:
            session: GameActivity
            await session.end()
            del PLAYTIME_SESSIONS[user_id]['sessions'][session.app.id]
            if len(PLAYTIME_SESSIONS[user_id]['sessions']) == 0:
                del PLAYTIME_SESSIONS[user_id]
