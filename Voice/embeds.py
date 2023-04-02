import time
import discord
from Emojis.emoji_generator import get_guild_emoji
from Voice.VoiceActivity import VoiceActivity, VOICE_SESSIONS
from Voice.track_voice import get_recent_voice_activity, get_voicetime_today, last_voiced_server
from misc.misc import locate_htable_obj, time_elapsed, today
from tunables import *


# Generic voicetime embed when complicated queries are not supplied
async def voicetime_embed(
                client: discord.Client,
                user: discord.User,
                guild: discord.Guild,
                offset=0,
                page_size=10,
                updates=0,
                voicetime=0,
                avg_session="`None`",
                voicetime_guild=0) -> discord.Embed:
    num = 0
    recent_activity = await get_recent_voice_activity(user=user, page_size=page_size, offset=offset)
    current: VoiceActivity = locate_htable_obj(map=VOICE_SESSIONS, key=user.id)[0]
    voicetime_today = await get_voicetime_today(user_id=user.id)
    current_time = int(time.time())
    

    temp = []
    temp.append(f":pencil: Name: {user.mention}\n")

    if current is not None:
        voicetime = voicetime + current.time_elapsed
        if current.guild == guild:
            voicetime_guild = voicetime_guild + current.time_elapsed

    # Total voicetime (by user)
    if voicetime <= 0: voicetime = "`None`"
    else: voicetime = f"`{time_elapsed((voicetime), 'h')}` | `{round(time_elapsed((voicetime), 'r'), 1)}h`"
    temp.append(f":microphone2: Total Voicetime: {voicetime}\n")

    # Total guild voicetime (by user)
    if voicetime_guild <= 0: voicetime_guild = "`None`"
    else: voicetime_guild = f"`{time_elapsed(voicetime_guild, 'h')}` | `{round(time_elapsed(voicetime_guild, 'r'), 1)}h`"
    temp.append(f"{await get_guild_emoji(client, guild)} **{guild.name}** Voicetime: {voicetime_guild}\n")

    temp.append(f":chart_with_upwards_trend: Average Session: {avg_session}\n")
    temp.append(f":date: Voicetime today: ")


    if current is not None: # currently in voice chat -> has voice time
        guild = client.get_guild(current.guild.id)
        
        current_voicetime_today = voicetime_today
        if current.start_time >= today():
            current_voicetime_today += current_time - current.start_time
        else:
            current_voicetime_today += current_time - today()
        
        temp.append(f"`{time_elapsed(current_voicetime_today, 'h')}`\n\n")
        ct = int(time.time())
        temp.append(f"{await get_guild_emoji(client, guild)} ")
        temp.append(f"<t:{current.start_time}:R> ")
        temp.append(f"**{guild.name}** ")
        temp.append(f"`{time_elapsed((ct - current.start_time), 'h')}` _(current)_\n\n")
    elif voicetime_today > 0: temp.append(f"`{time_elapsed(voicetime_today, 'h')}`\n\n") # has voicetime, but not currently in voice chat
    else: temp.append("`None`\n\n") # No voicetime today


    if recent_activity is None: temp.append("`No recent voice activity.`")
    else:
        for item in recent_activity:
            guild = client.get_guild(int(item[1]))
            if guild is None: guild_name = "_(unknown guild)_ "
            else: guild_name = f"**{guild.name}** "
            if guild is not None: temp.append(f"{await get_guild_emoji(client, guild)} ")
            else: temp.append(":grey_question: ")
            temp.append(f"<t:{item[0]}:R> ")
            temp.append(guild_name)
            temp.append(f"`{time_elapsed(item[2], 'h')}`\n")
            num += 1


    embed = discord.Embed (
        title = f'{user.name} voicetime statistics',
        color = GLOBAL_EMBED_COLOR,
        description=f"{''.join(temp)}"
    )
    embed.set_thumbnail(url=user.avatar)
    if num >= page_size: embed.set_footer(text=f"Showing {(offset + 1):,} - {(offset + page_size):,} of {updates:,} updates")
    elif updates > 0: embed.set_footer(text=f"Showing {(offset + 1):,} - {updates:,} of {updates:,} updates")
    return embed


async def voicetime_search_embed(
            user: discord.Member,
            client: discord.Client,
            search_results,
            sort,
            page_size,
            results,
            user_scope: bool,
            guild=None,
            offset=0,
            vtquery=None,
            total=0,
            avg=0) -> discord.Embed:

    temp = []
    if user_scope: temp.append(f":pencil: Name: {user.mention}\n")
    if not user_scope and guild is None: temp.append(f"{await get_guild_emoji(client, user.guild)} Guild: **{user.guild}**\n")
    elif user_scope and guild is not None and type(guild) is not str:
        temp.append(f"{await get_guild_emoji(client, guild)} Guild: **{guild}**\n")
    elif user_scope and guild is not None: temp.append(f":shield: Guild: **{guild}**\n")
    detailed = False
    sc = False
    mp = False
    match sort:
        case 'la':
            temp.append("<:ASC_sort:1019497227896500264> Sort: `Least Active`\n")
            mp = True
        case 'ls':
            temp.append("<:DESC_sort:1019497286482538566> Sort: `Longest Session [detailed]`\n")
            detailed = True
        case 'ma':
            temp.append("<:DESC_sort:1019497286482538566> Sort: `Most Active`\n")
            mp = True
        case 'sc':
            temp.append("<:DESC_sort:1019497286482538566> Sort: `Session Count`\n")
            sc = True
        case _:
            temp.append(":clock2: Sort: `Latest [detailed]`\n")
            detailed = True
        
    temp.append(f":hourglass: Voicetime: `{'>1m' if vtquery is None else vtquery}`\n")
    temp.append(":bar_chart: __Search Statistics__:\n")
    temp.append(f"\u200b \u200b├─:stopwatch: Total Voicetime: `{time_elapsed(total, 'h')}` | `{round(time_elapsed(total, 'r'), 1)}h`\n")
    temp.append(f"\u200b \u200b└─:chart_with_upwards_trend: Average Session: `{time_elapsed(avg, 'h')}`\n\n")
    
    num = 1
    for i, item in enumerate(search_results):
        guild = client.get_guild(int(item[1]))

        # Whether or not we are numbering results
        # and identifying user that ran cmd
        if mp or sc:
            if len(item) == 6 and str(user.id) == item[5]:
                temp.append(":index_pointing_at_the_viewer: ")
            else: temp.append(f"`{i + 1 + offset}.` ")

        # Guild emoji
        temp.append(f"{await get_guild_emoji(client, guild)} ")
        
        # If we need to check the last time the user was in voice
        # chat in a given guild
        if mp or sc:
            temp.append(
                f"<t:{await last_voiced_server(user_id=(int(item[5]) if len(item) == 6 else user.id), server_id=item[1])}:R> "
                )
        else:
            temp.append(f"<t:{item[4]}:R> ")
        temp.append(f"{f'**{guild}**' if guild is not None else '_(unknown guild)_'} ")
        
        # Time elapsed + hour count OR session count
        if mp: temp.append(f"`{time_elapsed(int(item[2]), 'h')}` | `{round(time_elapsed(int(item[2]), 'r'), 1)}h`")
        elif sc: temp.append(f"`{item[4]} Session{'' if item[4] <= 1 else 's'}` ")
        else: temp.append(f"`{time_elapsed(int(item[2]), 'h')}`")
        
        # If not user scope, append the owner of this entry
        if len(item) == 6: temp.append(f" <@{item[5]}>")
        temp.append("\n")

        num += 1
    
    embed = discord.Embed (
        title = "Voicetime Search Results",
        color = GLOBAL_EMBED_COLOR,
        description=f"{''.join(temp)}"
    )
    total_sessions = 0
    tot_ses_str = ""
    try: # lazy temporary fix for session count
        if sc:
            print(count)
            for count in search_results:
                total_sessions += count[5]
            if total_sessions > 1: tot_ses_str = f". {total_sessions:,} sessions on this page."
            else: tot_ses_str = f". {total_sessions:,} session on this page."
    except: pass

    if num > page_size:
        embed.set_footer(text=f"Showing {(offset + 1):,} - {(offset + page_size):,} of {results:,} results{tot_ses_str}")
    elif results > 0:
        embed.set_footer(text=f"Showing {(offset + 1):,} - {results:,} of {results:,} results{tot_ses_str}")
    else: embed.set_footer(text="Showing 0 - 0 of 0 results")
    if user_scope: embed.set_thumbnail(url=user.avatar)
    elif not user_scope: embed.set_thumbnail(url=user.guild.icon)
    return embed