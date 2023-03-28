import discord
from Database.GuildObjects import MikoMember
from tunables import tunables, GLOBAL_EMBED_COLOR
from Settings.settings import Setting

def settings_initial(interaction: discord.Interaction) -> discord.Embed:
        
    temp = []
    temp.append(
        f"Most {interaction.client.user.mention} Commands and features can\n"
        "be toggled at any time using this menu."
        "\n\n"
        "__**Select which settings to modify**__:\n\n"
        f"• 🙋‍♂️ **Yourself**: Change settings that affect only you (not guild-specific)\n\n"
        # "\nor\n"
        "• 🛡 **Guild**: Change settings that affect all users in this guild.\n"
        "Note: Must have `Manage Server` permission to modify these settings."
    )

    embed = discord.Embed (
        color = GLOBAL_EMBED_COLOR,
        description=f"{''.join(temp)}"
    )
    embed.set_author(icon_url=interaction.client.user.avatar, name="Miko Settings")
    return embed

async def settings_list(u: MikoMember, settings: list) -> discord.Embed:

    temp = []
    temp.append("__Select a setting to modify__:\n\n")

    server = False
    for setting in settings:
        setting: Setting = setting
        if setting.table == "SERVERS": server = True
        temp.append("• ")
        temp.append(f"{setting.emoji} ")
        temp.append(f"`{setting.name}`: ")
        temp.append(f"*{setting.desc}*")
        if server: temp.append(f"{await setting.value_str(server_id=u.guild.id)}")
        else: temp.append(f"{await setting.value_str(user_id=u.user.id)}")
        temp.append("\n")


    embed = discord.Embed (
        color = GLOBAL_EMBED_COLOR,
        description=f"{''.join(temp)}"
    )
    embed.set_author(
        icon_url=u.guild.icon if server else await u.user_avatar,
        name=f"{u.guild if server else await u.username} Settings"
    )
    return embed

async def setting_embed(u: MikoMember, s: Setting) -> discord.Embed:

    temp = []
    temp.append("• ")
    temp.append(f"{s.emoji} ")
    temp.append(f"`{s.name}`: ")
    temp.append(f"*{s.desc}*")
    if s.table == "SERVERS":
        temp.append(f"{await s.value_str(server_id=u.guild.id)}")
    elif s.table == "USER_SETTINGS":
        temp.append(f"{await s.value_str(user_id=u.user.id)}")
    temp.append("\n\n")

    temp.append("Press **Confirm** to set this setting to:")
    if s.table == "SERVERS":
        temp.append(f"{await s.value_str(server_id=u.guild.id, invert=True)}")
    elif s.table == "USER_SETTINGS":
        temp.append(f"{await s.value_str(user_id=u.user.id, invert=True)}")


    embed = discord.Embed (
        title=f"You are choosing to modify the following setting:",
        color = GLOBAL_EMBED_COLOR,
        description=f"{''.join(temp)}"
    )
    embed.set_author(
        icon_url=u.guild.icon if s.table == 'SERVERS' else await u.user_avatar,
        name=f"{u.guild if s.table == 'SERVERS' else f'{await u.username} Personal'} Settings"
    )
    return embed

async def setting_toggled(u: MikoMember, s: Setting) -> discord.Embed:

    temp = []
    temp.append(f"**{s.name}** is now")
    if s.table == "SERVERS":
        temp.append(f"{await s.value_str(server_id=u.guild.id)}")
    elif s.table == "USER_SETTINGS":
        temp.append(f"{await s.value_str(user_id=u.user.id)}")

    embed = discord.Embed (
        title = "Success!",
        color = GLOBAL_EMBED_COLOR,
        description=f"{''.join(temp)}"
    )
    return embed