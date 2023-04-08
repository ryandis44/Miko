from socket import create_server
import discord
import time
from datetime import datetime
from num2words import num2words
from dotenv import load_dotenv
from Database.database_class import AsyncDatabase
from misc.misc import human_format, percentage_two_decimals
from tunables import *

db = AsyncDatabase("Database.database.py")

def if_not_list_create_list(var):
    if type(var) is not list:
        temp = [var]
        return temp
    else:
        users = [item[0] for item in var]
        return users
    
def combine_two_items_list(list):
    temp = []
    for item in list:
        temp.append(item[1])
        temp.append(item[0])
    return temp

def add_all_list_items(li):
    if type(li) is not list:
        return li
    val = 0
    for num in li:
        val += num[0]
    return val

# Several GETTER, SETTER, and DELETER functions
async def get_channels_by_message_count_nobots(server):
    sel_cmd = (
        "SELECT channel_id,cnt "
        "FROM TOP_CHANNELS_PER_GUILD_MSG_COUNT_NOBOTS "
        f"WHERE server_id={server.id}"
    )
    return await db.execute(sel_cmd)

async def get_private_channels_by_message_count(server):
    sel_cmd = f"SELECT SUM(cnt) FROM CHANNEL_MESSAGES_NOBOTS WHERE server_id={server.id} AND private='TRUE'"
    val = await db.execute(sel_cmd)
    if val is None: return 0
    else: return int(val)

async def add_react_to_user(user_id, server) -> bool:
    sel_cmd = f"SELECT react_true_false FROM USERS WHERE user_id={user_id} AND server_id={server.id}"
    # If the user is already being reacted to, we want to
    # return FALSE so that our 'if' statement in our parent
    # function will use its' else statement.
    temp = await db.execute(sel_cmd)
    if temp == "TRUE":
        return False

    upd_cmd = f"UPDATE USERS SET react_true_false=\"TRUE\" WHERE user_id={user_id} AND server_id={server.id}"
    await db.execute(upd_cmd)
    return True

async def add_react_all_to_user(user_id, server):
    sel_cmd = f"SELECT react_all_true_false FROM USERS WHERE user_id={user_id} AND server_id={server.id}"
    # If the user is already being reacted to, we want to
    # return FALSE so that our 'if' statement in our parent
    # function will use its' else statement.
    temp = await db.execute(sel_cmd)
    if temp == "TRUE":
        return False

    upd_cmd = f"UPDATE USERS SET react_all_true_false=\"TRUE\" WHERE user_id={user_id} AND server_id={server.id}"
    await db.execute(upd_cmd)
    return True

async def add_rename_any_user(user_id, server):
    sel_cmd = f"SELECT rename_any_true_false FROM USERS WHERE user_id={user_id} AND server_id={server.id}"
    # If the user is already being reacted to, we want to
    # return FALSE so that our 'if' statement in our parent
    # function will use its' else statement.
    temp = await db.execute(sel_cmd)
    if temp == "TRUE":
        return False

    upd_cmd = f"UPDATE USERS SET rename_any_true_false=\"TRUE\" WHERE user_id={user_id} AND server_id={server.id}"
    await db.execute(upd_cmd)
    return True

async def add_bot(bot_id, server):
    sel_cmd = f"SELECT is_bot FROM USERS WHERE user_id={bot_id} AND server_id={server.id}"
    # If the user is already being reacted to, we want to
    # return FALSE so that our 'if' statement in our parent
    # function will use its' else statement.
    temp = await db.execute(sel_cmd)
    if temp == "TRUE":
        return False

    upd_cmd = f"UPDATE USERS SET is_bot=\"TRUE\" WHERE user_id={bot_id} AND server_id={server.id}"
    await db.execute(upd_cmd)
    return True

async def del_react_to_user(user_id, server):
    sel_cmd = f"SELECT react_true_false FROM USERS WHERE user_id={user_id} AND server_id={server.id}"
    # If the user is not already being reacted to, we want to
    # return FALSE so that our 'if' statement in our parent
    # function will use its' else statement.
    temp =  await db.execute(sel_cmd)
    if temp == "FALSE" or temp == "":
        return False

    upd_cmd = f"UPDATE USERS SET react_true_false=\"FALSE\" WHERE user_id={user_id} AND server_id={server.id}"
    await db.execute(upd_cmd)
    return True

async def del_react_all_to_user(user_id, server):
    sel_cmd = f"SELECT react_all_true_false FROM USERS WHERE user_id={user_id} AND server_id={server.id}"
    # If the user is not already being reacted to, we want to
    # return FALSE so that our 'if' statement in our parent
    # function will use its' else statement.
    temp =  await db.execute(sel_cmd)
    if temp == "FALSE" or temp == "":
        return False

    upd_cmd = f"UPDATE USERS SET react_all_true_false=\"FALSE\" WHERE user_id={user_id} AND server_id={server.id}"
    await db.execute(upd_cmd)
    return True

async def del_rename_any_user(user_id, server):
    sel_cmd = f"SELECT rename_any_true_false FROM USERS WHERE user_id={user_id} AND server_id={server.id}"
    # If the user is not already being reacted to, we want to
    # return FALSE so that our 'if' statement in our parent
    # function will use its' else statement.
    temp = await db.execute(sel_cmd)
    if temp == "FALSE" or temp == "":
        return False

    upd_cmd = f"UPDATE USERS SET rename_any_true_false=\"FALSE\" WHERE user_id={user_id} AND server_id={server.id}"
    await db.execute(upd_cmd)
    return True

async def del_bot(bot_id, server):
    sel_cmd = f"SELECT is_bot FROM USERS WHERE user_id={bot_id} AND server_id={server.id}"
    # If the user is not already being reacted to, we want to
    # return FALSE so that our 'if' statement in our parent
    # function will use its' else statement.
    temp = await db.execute(sel_cmd)
    if temp == "FALSE" or temp == "":
        return False

    upd_cmd = f"UPDATE USERS SET is_bot=\"FALSE\" WHERE user_id={bot_id} AND server_id={server.id}"
    await db.execute(upd_cmd)
    return True






# User statistics embed
async def user_info_embed(u):
    await u.increment_statistic('USER_INFO_TIMES_REFERENCED')
    usr_total_msg = await u.user_messages
    usernames = await u.usernames
    user_created_at = int(u.user.created_at.timestamp())
    temp = []
    temp.append(f":pencil: Name: {u.user.mention}\n"+
                f"<a:right_arrow_animated:1011515382672150548> Account created <t:{user_created_at}:R>\n"+
                f"<a:right_arrow_animated:1011515382672150548> First joined <t:{await u.first_joined}:R>\n"+
                f"<a:right_arrow_animated:1011515382672150548> `{str(num2words(await u.member_number, to = 'ordinal_num'))}` user to join **{u.guild}**\n"+
                f"<a:right_arrow_animated:1011515382672150548> Total messages sent in this server: `{usr_total_msg:,}`\n"+
                f"<a:right_arrow_animated:1011515382672150548> Messages sent in this server today: `{await u.user_messages_today}`\n")


    placement = await u.message_rank
    guild_messages = await u.guild_messages
    temp.append("\n")
    temp.append(f"**{u.guild}** total messages: `{human_format(guild_messages)}`\n")

    if placement == -1:
        temp.append('`This is a` <:bot1:963660599810740264><:bot2:963660577379598336> `account and does not have\na message ranking.`\n\n')
    else:
        temp.append(f'`#{placement}` out of all users on this server.\n\n')

    percentage = (usr_total_msg / guild_messages) * 100
    percentage_nobots = (usr_total_msg / await u.guild_messages_nobots) * 100
    temp.append(f"Percentage of server messages: `{str('{:.2f}'.format(round(percentage, 2)))}%`")
    if placement != -1:
        temp.append(f" (`{str('{:.2f}'.format(round(percentage_nobots, 2)))}%` _without_ bots)")
    
    if len(usernames) <= 2:
        temp.append("\n\n")
        temp.append(f"<:nametag:1011514395630764032> This user has no recored account name changes.")
    elif len(usernames) >= 4:
        temp.append("\n\n")
        temp.append(f"<:nametag:1011514395630764032> This user has `{int(len(usernames)/2)}` recored account name changes")
        if len(usernames) > 10:
            temp.append(" (showing last 5):\n")
        else:
            temp.append("\n")
        for i, name in enumerate(usernames):
            if i == 10:
                break
            if i % 2 != 0:
                temp.append(f" - <t:{name}:R>")
                if i == 1: temp.append(" _(current)_\n")
                else: temp.append("\n")
            else:
                temp.append(f"\u200b \u200b <a:right_arrow_animated:1011515382672150548> `{name}`")


    embed = discord.Embed (
        title = f'{await u.username} user info',
        color = GLOBAL_EMBED_COLOR,
        description=f"{''.join(temp)}"
    )
    embed.set_thumbnail(url=await u.user_avatar)
    return embed

# mstop embed
async def top_users_embed_server(g):
    users = await g.top_ten_total_messages_nobots #get_top_ten_total_messages_nobots(g.guild)
    total_server_messages = await g.guild_messages
    total_server_messages_nobots = await g.guild_messages_nobots
    total_msgs_today = await g.guild_messages_today

    temp = []
    temp.append("\n")
    temp.append(f"Total server messages: `{human_format(total_server_messages)}` (_with_ bots)\n")
    temp.append(f"Total server messages: `{human_format(total_server_messages_nobots)}` (_without_ bots)\n")
    temp.append(f"Server messages today: `{human_format(total_msgs_today)}`\n")

    temp.append("\n`# msg` [`% of server msgs`]\n")

    total_msg_top_users = 0
    for i, user in enumerate(users):
        string = f"{i+1}. `{human_format(int(user[0]))}` [`{str('{:.2f}'.format(round((int(user[0]) / total_server_messages_nobots) * 100, 2)))}%`] — <@{user[1]}>\n"
        temp.append(string)
        total_msg_top_users += int(user[0])
    percentage = (total_msg_top_users / total_server_messages) * 100
    percentage_nobots = (total_msg_top_users / total_server_messages_nobots) * 100


    temp.append(f"\nTotal messages from these users: `{human_format(total_msg_top_users)}`")
    temp.append(f"\nPercentage these users hold: `{str('{:.2f}'.format(round(percentage, 2)))}%` (`{str('{:.2f}'.format(round(percentage_nobots, 2)))}%` _without_ bots)")
    
    embed = discord.Embed (
        title = f'Top User Messages in {g.guild}',
        color = GLOBAL_EMBED_COLOR,
        description=f"{''.join(temp)}"
    )
    embed.set_thumbnail(url=g.guild.icon)
    embed.set_image(url=g.guild.banner)
    return embed

async def top_channels_embed_server(c):
    channels = await get_channels_by_message_count_nobots(c.guild)
    private_msg_count = await get_private_channels_by_message_count(c.guild)
    total_server_messages = await c.guild_messages
    total_server_messages_nobots = await c.guild_messages_nobots
    current_channel_msg_count = await c.channel_messages_nobots

    temp = []
    temp.append("\n")
    temp.append(f"Total server messages: `{human_format(total_server_messages)}` (_with_ bots)\n")
    temp.append(f"Total server messages: `{human_format(total_server_messages_nobots)}` (_without_ bots)\n\n")
    temp.append(f"`{current_channel_msg_count:,}` [`{percentage_two_decimals(current_channel_msg_count, total_server_messages_nobots)}%`] — {c.channel.mention} _(current channel)_\n")

    temp.append("\n`# msg` [`% of server msgs`] [no bots]\n")
    
    count = 0
    for channel in channels:
        temp.append(f'{count + 1}. `{human_format(int(channel[1]))}` [`{percentage_two_decimals(int(channel[1]), total_server_messages_nobots)}%`]'+
                    f' — <#{channel[0]}>\n')
        count += 1
    
    if private_msg_count > 0:
        temp.append(f"{count + 1}. `{human_format(private_msg_count)}` [`{percentage_two_decimals(private_msg_count, total_server_messages_nobots)}%`] — _Private channels_\n")
    
    embed = discord.Embed (
        title = f'Top Channel Messages in {c.guild}',
        color = GLOBAL_EMBED_COLOR,
        description=f"{''.join(temp)}"
    )
    embed.set_thumbnail(url=c.guild.icon)
    embed.set_image(url=c.guild.banner)
    return embed

# generic listing embed
async def generic_list_embed(u, list: str):

    list_name = "NULL"
    member_or_bot = "member"

    match list.lower():

        case "react":
            list_name = "Reaction"
            users_temp = await u.clown_react_users

        case "reactall":
            list_name = "ReactAll"
            users_temp = await u.react_all_users
        
        case "bot":
            list_name = "Bot"
            member_or_bot = "bot"
            users_temp = await u.bot_list
        
        case "rename":
            list_name = "Rename"
            users_temp = await u.rename_users
        
        case "renameany":
            list_name = "Rename Any"
            users_temp = await u.renamehell_members
        
        case _:
            list_name = "NULL"
            member_or_bot = "NULL"
            users_temp = []




    temp = []               
    if len(users_temp) == 0:
        temp.append(f"There are no members on the {list_name.lower()}\nlist for **{u.guild}**")
    else:
        temp.append(f'`{len(users_temp)}` ')
        if len(users_temp) == 1:
            temp.append(f'{member_or_bot} is')
        else:
            temp.append(f'{member_or_bot}s are')
        temp.append(f' on the {list_name.lower()} list\nfor **{u.guild}**:\n')

    list_iterator = 0
    for user in users_temp:
        if list_iterator % 3 == 0 and list_iterator != 0:
            temp.append("\n")
        if list_iterator == (len(users_temp) - 1):
            temp.append(f'<@{user}>')
        else:
            temp.append(f'<@{user}>, ')
            list_iterator += 1

    embed = discord.Embed (
    title = f'{list_name} List',
    color = GLOBAL_EMBED_COLOR,
    description=f"{''.join(temp)}"
    )
    embed.set_thumbnail(url=u.guild.icon)
    return embed