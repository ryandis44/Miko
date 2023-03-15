import discord
from Database.database_class import AsyncDatabase
from PIL import Image
import requests, aiohttp
from io import BytesIO
from discord.utils import get
import os
from tunables import *
from dotenv import load_dotenv

load_dotenv()
aeg = AsyncDatabase("Emojis.emoji_generator.py")

async def get_guild_emoji(client: discord.Client, guild: discord.Guild) -> discord.Emoji:

    sel_cmd = f"SELECT emoji FROM SERVERS WHERE server_id='{guild.id}'"
    emoji_id = await aeg.execute(sel_cmd)

    if emoji_id is None:
        emoji = await create_guild_emoji(guild)
    else: emoji = client.get_emoji(int(emoji_id))
    if emoji is None:
        upd_cmd = f"UPDATE SERVERS SET emoji=NULL WHERE server_id='{guild.id}'"
        await aeg.execute(upd_cmd)
        emoji = await get_guild_emoji(client, guild)
    return emoji

def get_emoji_url(s: str) -> str:

    msg = s.split(':')
    emoji_name = msg[1]
    msg = msg[-1][:-1]

    if s[1:3] == "a:": return f"https://cdn.discordapp.com/emojis/{msg}.gif", emoji_name
    return f"https://cdn.discordapp.com/emojis/{msg}.png", emoji_name

async def create_guild_emoji(guild: discord.Guild):

    if guild.icon is None: return "❔"
    url = guild.icon.url[:-4] # removes 1024
    url = url + "32" # resize image
    async with aiohttp.ClientSession() as ses:
        async with ses.get(url) as r:
            if r.status in range(200, 299):
                img = BytesIO(await r.read())
                b = img.getvalue()
            else:
                print(f"Something went wrong when creating {guild} emoji: {r.status}")
                return None

    try:
        emoji: discord.Emoji = await guild.create_custom_emoji(
            image=b,
            name=f"miko_ctx_{guild.id}",
            roles=None,
            reason="Guild Emoji created for use in embeds mentioning this Guild"
        )
    except: emoji = None


    if emoji is None: return "❗"
    
    upd_cmd = f"UPDATE SERVERS SET emoji='{emoji.id}' WHERE server_id='{guild.id}'"
    await aeg.execute(upd_cmd)
    return emoji

async def regen_guild_emoji(client: discord.Client, guild: discord.Guild) -> None:
    sel_cmd = f"SELECT emoji FROM SERVERS WHERE server_id='{guild.id}'"
    emoji_id = await aeg.execute(sel_cmd)

    if emoji_id is not None:
        emoji = client.get_emoji(int(emoji_id))
        if emoji is not None:
            await emoji.delete()
            upd_cmd = f"UPDATE SERVERS SET emoji=NULL WHERE server_id='{guild.id}'"
            await aeg.execute(upd_cmd)
    await get_guild_emoji(client, guild)
    return