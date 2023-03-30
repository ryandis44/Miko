import asyncio
import time
import discord
from Plex.background import end_of_week_int
from Plex.embeds import plex_multi_embed, plex_upcoming
from Voice.VoiceActivity import VoiceActivity, VOICE_SESSIONS
from Database.GuildObjects import MikoMember
from Database.database_class import AsyncDatabase
from Polls.UI import active_polls
import aiohttp

from tunables import tunables
db = AsyncDatabase("async_processes.py")

client: discord.Client = None
def set_async_client(c):
    global client
    client = c


async def heartbeat():
    num = 1
    while True:
        if num % 10 == 0:
            try: await voice_heartbeat()
            except Exception as e: print(f"some shit stopped working idk [voice heartbeat]: {e}")

        if num % 60 == 0:
            try: await check_notify()
            except Exception as e: print(f"Plex notify check failed, trying again in 60 seconds...: {e}")

        # Check if miko is still in guilds
        # if num % 3600 == 0:
        #     try:
        #     except Exception as e: print()

        if num == 3700: num = 0
        num += 1
        # print(num)
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