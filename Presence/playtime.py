import time
import discord
import uuid
from discord.utils import get
from Presence.GameActivity import GameActivity
from utils.HashTable import HashTable
from Database.database import if_not_list_create_list
from Database.database_class import AsyncDatabase
from misc.misc import time_elapsed, today
from tunables import *


# For every active session, end session when bot terminates

sessions_hash_table = HashTable(10000)

db = AsyncDatabase("Presence.Presence.py")

def start_time(activity):
    try: return int(activity.start.timestamp())
    except: return None

def sesh_id(activity):
    try: return activity.session_id
    except: return None

async def fetch_playtime_sessions(client):
    async def restore(member, app_id, i, st):
        if not tunables('TRACK_PLAYTIME'): return
        g = GameActivity(member, app_id, i, st)
        await g.ainit()
        sessions_hash_table.set_val(member.id, g)
        return

    sel_cmd = "SELECT value FROM PERSISTENT_VALUES WHERE variable='GLOBAL_REBOOT_TIME_ACTIVITY'"
    end_time = await db.execute(sel_cmd)
    if end_time is None:
        sel_cmd = "SELECT end_time FROM PLAY_HISTORY WHERE end_time!='-1' ORDER BY end_time DESC LIMIT 1"
        end_time = await db.execute(sel_cmd)
    
    if end_time is None or end_time == []:
        print("Could not fetch a time to restore any playtime sessions.")
        return
    
    sel_cmd = (
        "SELECT user_id, session_id, app_id, start_time FROM PLAY_HISTORY "+
        f"WHERE end_time={end_time}"
    )
    val = list(await db.execute(sel_cmd))
    rst = 0
    t = int(time.time()) - tunables('THRESHOLD_RESUME_REBOOT_GAME_ACTIVITY')
    
    # Not very fast, but only way to achieve game session restoration
    for guild in client.guilds:
        if val == []: break
        for member in guild.members:
            if val == []: break
            if val != [] and any(str(member.id) in sl for sl in val) and member.activities != ():
                

                # Find which iteration of val the member.id was matched to
                outer = 0
                found = False
                for i, entry in enumerate(val):
                    for user in entry:
                        if user == str(member.id):
                            found = True
                            break
                    if found:
                        outer = i
                        break
                
                restored = f"> Restored {member}'s playtime session"
                cur_playing = find_type_playing(member)
                activity = member.activities[cur_playing[1]]
                if cur_playing[0]: game = await identify_current_application(activity, has_app_id(activity))
                else: continue
                session_id = sesh_id(activity)

                st = start_time(activity)

                # If the current app id is equal to the playtime database entry, continue
                if game[1] == val[outer][2]:
                    
                    # If the (member.)activity has supplied a start time, check if it is equal to the start time of
                    # the entry we have in our database. If so, restore session.
                    if st is not None and (st == val[outer][3] or end_time >= t):
                        if session_id is None:
                            await restore(member, game[1], cur_playing[1], st)
                            print(restored)
                            rst += 1
                        
                        # If the (discord provided) session id matches the id
                        # in the database entry, restore regardless of end time
                        elif val[outer][1] is not None and session_id == val[outer][1]:
                            await restore(member, game[1], cur_playing[1], st)
                            print(restored + f" from Session ID {session_id}")
                            rst += 1

                    elif st is None:

                        # If we do not have a session id or a start time but 
                        # the end time is less than 5 minutes ago and the user 
                        # is playing the same game they were <5 minutes ago, restore
                        if session_id is None and end_time >= t:
                            await restore(member, game[1], cur_playing[1], val[outer][3])
                            print(restored)
                            rst += 1
                        
                        # If the (discord provided) session id matches the id
                        # in the database entry, restore regardless of end time
                        elif val[outer][1] is not None and session_id == val[outer][1]:
                            await restore(member, game[1], cur_playing[1], val[outer][3])
                            print(restored + f" from Session ID {session_id}")
                            rst += 1
                
                del val[outer] # Done processing this user, delete from memory

    if rst > 0:
        print(f"Restored {rst} playtime sessions.")
        print("Playtime session restoration complete.")
    else: print("No playtime sessions were restored.")
    return





def translate_application_name(name):
    return name.replace("'", "''")

async def get_app_from_str(input):
    sel_cmd = f"SELECT name,app_id,emoji FROM APPLICATIONS WHERE name LIKE '{'%' + input + '%'}' AND counts_towards_playtime!='FALSE' LIMIT 10"
    return await db.execute(sel_cmd)


# Used to block tracking console-based application IDs.
# Doing so allows tracking individual games, regardless
# of the device it is being played on.
# tunables('BLACKLISTED_APPLICATION_IDS)

async def identify_current_application(app, has_id):
    tr_name = translate_application_name(app.name)

    info = [None, -1]

    try: # Treat a blacklisted application id as one that does not have a discord id
        if has_id and str(app.application_id) in tunables('BLACKLISTED_APPLICATION_IDS').split(): has_id = False
    except: pass

    if has_id:
        sel_cmd = f"SELECT * FROM APPLICATIONS WHERE app_id='{app.application_id}'"
        val = await db.execute(sel_cmd)
        if not db.exists(len(val)):
            print(f"New application \"{tr_name}\" found! Saving in database with discord application ID '{app.application_id}'")
            ins_cmd = f"INSERT INTO APPLICATIONS (name,app_id,has_discord_id) VALUES ('{tr_name}', '{app.application_id}', 'TRUE')"
            await db.execute(ins_cmd)
            info = [tr_name, app.application_id]
        else:
            info = [translate_application_name(val[0][0]), val[0][1]]
            if val[0][0] != app.name:
                print(f"Updating application name {val[0][0]} to {tr_name} with discord ID {app.application_id} in database.")
                upd_cmd = f"UPDATE APPLICATIONS SET name='{tr_name}' WHERE app_id='{app.application_id}'"
                await db.execute(upd_cmd)

    elif not has_id:
        sel_cmd = f"SELECT name,app_id FROM APPLICATIONS WHERE name='{tr_name}'"
        val = await db.execute(sel_cmd)
        if not db.exists(len(val)):
            aid = None
            while True: # Make sure we do not have duplicate application id
                aid = uuid.uuid4().hex
                sel_check_cmd = f"SELECT * FROM APPLICATIONS WHERE app_id='{aid}'"
                if await db.execute(sel_check_cmd) == []: break
            print(f"New application \"{tr_name}\" found! Saving in database with non-discord application ID {aid}")
            ins_cmd = f"INSERT INTO APPLICATIONS (name,app_id) VALUES ('{tr_name}', '{aid}')"
            await db.execute(ins_cmd)
            info = [tr_name, aid]
        else:
            info = [val[0][0], val[0][1]]
    return info

async def identify_application(bef_app, cur_app, bef_has_id, cur_has_id, status):

    before = [None, -1]
    current = [None, -1]

    match status:
        case "start":
            current = await identify_current_application(cur_app, cur_has_id)

        case "stop":
            before = await identify_current_application(bef_app, bef_has_id)

        case "switch":
            before = await identify_current_application(bef_app, bef_has_id)
            current = await identify_current_application(cur_app, cur_has_id)

    return [before, current]

# Returns [True, i], i being the activity with playing status
# Else returns [False, -1], no playing status found
def find_type_playing(user):
    if user is None: return [False, -1]

    for i, activity in enumerate(user.activities):
        try: # When calling .type and there is no activity, discord throws an error. Must catch with try except.
            if activity.type is discord.ActivityType.playing:
                return [True, i]
        except:
            return [False, i]
    return [False, -1]

def has_app_id(activity):
        try: 
            if activity.application_id is None: return False
        except: return False
        return True

async def determine_activity(bef: discord.Member, cur: discord.Member, u, scrape=False):


    # First, we need to determine if the user activity has changed. Presence updates do not just include activity
    # updates, so we must filter out online presence, status messages, and other changes.
    #
    # Once we determine activity has changed, we need to determine if the activity the user is participating in
    # is 1) a game 2) has an application id from discord.
    #
    # After that, we need to determine what kind of activity change occurred: started activity, stopped activity,
    # or changed activity.
    #
    # Then, we must identify the game the user is playing and compare it to what we have in our database.
    #
    # Lastly, we determine if the user has started, stopped, or changed activities once again, and insert or update
    # playtime entries in our database


    # Determine if there is an activity change

    # If no change in activity, do nothing
    if cur.activities == bef.activities and not scrape:
        return

    cur_playing = find_type_playing(cur)
    cur_has_app_id = True
    if scrape: bef_playing = [False, -1]
    else: bef_playing = find_type_playing(bef)
    bef_has_app_id = True
    
    if cur_playing[0]:
        try:
            if cur.activities[cur_playing[1]].application_id is None:
                cur_has_app_id = False
        except:
            cur_has_app_id = False
        
    if bef_playing[0]:
        try:
            if bef.activities[bef_playing[1]].application_id is None:
                bef_has_app_id = False
        except:
            bef_has_app_id = False


    # Determine start, stop, or change
    game = None
    #start
    if cur_playing[0] and not bef_playing[0]: #start activity
        game = await identify_application(None, cur.activities[cur_playing[1]], bef_has_app_id, cur_has_app_id, "start")
    #stop
    if bef_playing[0] and not cur_playing[0]: #stop activity
        game = await identify_application(bef.activities[bef_playing[1]], None, bef_has_app_id, cur_has_app_id, "stop")
    #change
    if bef_playing[0] and cur_playing[0]: #switch activity
        game = await identify_application(bef.activities[bef_playing[1]], cur.activities[cur_playing[1]], bef_has_app_id, cur_has_app_id, "switch")

    # game[0][0] is BEFORE game name
    # game[0][1] is BEFORE game ID
    # game[1][0] is CURRENT game name
    # game[1][1] is CURRENT game ID

    async def start(user, app_id):
        if not await u.track_playtime: return

        val = sessions_hash_table.get_val(user.id)
        if val is None: # No current session, create one
            g = GameActivity(user, app_id, cur_playing[1])
            await g.ainit()
            sessions_hash_table.set_val(user.id, g)
        else:
            await val.close_activity_entry()
            sessions_hash_table.delete_val(user.id)
            g = GameActivity(user, app_id, cur_playing[1])
            await g.ainit()
            sessions_hash_table.set_val(user.id, g)

    async def stop(user, app_id, initial):
        try:
            await sessions_hash_table.get_val(user.id).close_activity_entry()
            sessions_hash_table.delete_val(user.id)
        except:
            await start(user, app_id)
            if initial: await stop(user, app_id, False)

    # Final activity status check: start, stop, change
    # start activity
    if game[1][0] is not None and game[0][0] is None:
        if sessions_hash_table.get_val(cur.id) is None: await start(cur, game[1][1])
        else: return
        
    # stopped activity
    if game[0][0] is not None and game[1][0] is None:
        await stop(bef, game[0][1], True)
            
    
    #game_change = False
    # changed activity
    if game[0][0] is not None and game[1][0] is not None and game[0] != game[1]:
        await stop(bef, game[0][1], True)
        await start(cur, game[1][1])
    
    if sesh_id(cur.activities[cur_playing[1]]) is not None:
        try: await sessions_hash_table.get_val(cur.id).update_session_id()
        except: pass

    return


async def get_total_playtime_user(user):
    sel_cmd = f"SELECT playtime FROM TOTAL_PLAYTIME WHERE user_id={user.id}"
    return await db.execute(sel_cmd)

def total_playtime_result(result):
    playtime = 0
    for val in result: playtime += val[3]
    return playtime

def avg_playtime_result(result):
    total = 0
    i = 0
    for val in result:
        if val[4] == 0: total += val[3]
        else: total += val[4]
        i += 1
    return int(total / i)

async def is_currently_playing(user: discord.User):
    global sessions_hash_table
    
    try:
        app: GameActivity = sessions_hash_table.get_val(user.id)
        if not await app.is_listed: return [False, 1, -1, ":question:"]

        return [
            True,
            app.start_time,
            app.act_name,
            await app.emoji
        ]
    except: # If we do not have the session stored in the hash table, we are not tracking it. Don't list
        return [False, 1, -1, ":question:"]

async def last_played(user_id, app_id):
    sel_cmd =f"SELECT end_time FROM PLAY_HISTORY WHERE user_id={user_id} AND app_id='{app_id}' AND end_time!=-1 ORDER BY end_time DESC LIMIT 1"
    return await db.execute(sel_cmd)
    
async def playtime_embed(u, limit, updates, playtime=[], avg_session="None", offset=0):
    current_time = int(time.time())
    playtime_today = await u.Presence.playtime_today
    recent_activity = await u.Presence.recent(limit=limit, offset=offset)
    currently_playing = await u.Presence.playing
    current_game_playtime = None
    num = 1

    temp = []
    temp.append(f":pencil: Name: {u.user.mention}\n")
    if playtime == [] and not currently_playing[0]:
        temp.append(f"Total playtime: `None`\n")
    elif currently_playing[0]:
        if playtime == []:
            playtime = 0
        current_game_playtime = (current_time - currently_playing[1])
        temp_playtime = current_game_playtime + playtime
    else:
        temp.append(f":stopwatch: Total playtime: `{time_elapsed(playtime, 'h')}` | `{round(time_elapsed(playtime, 'r'), 1)}h`\n")


    if playtime_today == 0 and not currently_playing[0]:
        temp.append(f":chart_with_upwards_trend: Average Session: `{avg_session}`\n")
        temp.append(f":date: Playtime today: `None`\n\n")
    elif currently_playing[0]:

        current_day_playtime = 0
        if playtime_today >= 0:
            current_day_playtime = playtime_today
        
        if currently_playing[1] >= today():
            current_day_playtime += current_time - currently_playing[1]
        else:
            current_day_playtime += current_time - today()
        
        temp.append(f":stopwatch: Total playtime: `{time_elapsed(temp_playtime, 'h')}` | `{round(time_elapsed(temp_playtime, 'r'), 1)}h`\n")
        temp.append(f":chart_with_upwards_trend: Average Session: `{avg_session}`\n")
        temp.append(f":date: Playtime today: `{time_elapsed(current_day_playtime, 'h')}`")
        temp.append("\n\n")
        if currently_playing[3] == ":question:":
            temp.append(f"`Current game did not provide a valid session ID`\n\n")
        else:
            temp.append(f"{currently_playing[3]} <t:{currently_playing[1]}:R> **{currently_playing[2]}** `{time_elapsed(current_game_playtime, 'h')}` _(current)_\n\n")
    else:
        temp.append(f":chart_with_upwards_trend: Average Session: `{avg_session}`\n")
        temp.append(f":date: Playtime today: `{time_elapsed(playtime_today, 'h')}`\n\n")
    
    
    
    if recent_activity is None and not currently_playing[0]:
        temp.append("`No recent activity.`")
    elif recent_activity is None and currently_playing[0]:
        temp.append("`No other recent activity.`")
    else:
        for item in recent_activity:
            temp.append(f"{item[0]} ")
            temp.append(f"<t:{item[1]}:R> ")
            temp.append(f"**{item[2]}** ")
            temp.append(f"`{time_elapsed(item[3], 'h')}`\n")
            num += 1


    embed = discord.Embed (
        title = f'{await u.username} playtime statistics',
        color = GLOBAL_EMBED_COLOR,
        description=f"{''.join(temp)}"
    )
    embed.set_thumbnail(url=await u.user_avatar)
    if num > limit: embed.set_footer(text=f"Showing {(offset + 1):,} - {(offset + limit):,} of {updates:,} updates")
    elif updates > 0: embed.set_footer(text=f"Showing {(offset + 1):,} - {updates:,} of {updates:,} updates")
    else: embed.set_footer(text="Showing 0 - 0 of 0 updates")
    return embed