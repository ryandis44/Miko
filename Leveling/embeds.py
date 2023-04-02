import discord
from Database.GuildObjects import MikoMember
from tunables import *
from misc.misc import time_elapsed

async def leveling_stats(u: MikoMember) -> discord.Embed:

    lc = u.leveling
    role: discord.Role = await lc.get_role()
    # role = u.user.top_role

    temp = []
    temp.append(f"Total XP: **{(await lc.xp):,}**")
    temp.append(f"\nLevel: **{await lc.level}** • {role.mention}")

    temp.append(f"\nMessages: `{await lc.msgs:,}`")
    temp.append(f"\nVoicetime: `{time_elapsed(await u.user_voicetime + await lc.active_voicetime, 'h')}`")

    # temp.append(f"\nMsg XP: **{lc.msg_xp:,}**")
    # temp.append(f"\nVoice XP: **{lc.voice_xp:,}**")

    embed = discord.Embed (
        color = GLOBAL_EMBED_COLOR,
        description=f"{''.join(temp)}"
    )
    embed.set_thumbnail(url=await u.user_avatar)
    embed.set_author(name=f"{await u.username} Leveling Stats", icon_url=role.display_icon)
    return embed