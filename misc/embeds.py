import os
import time
import discord
from misc.misc import sanitize_track_name, time_elapsed

from Playtime.playtime import last_played
from tunables import *

def plex_requests_embed():

    temp = []
    temp.append("Using __Overseerr__, a third-party software made for Plex, it is now possible ")
    temp.append("to request and directly add shows (including anime) and movies to Plex on your own.\n")

    temp.append("\n")
    temp.append("To request:")
    temp.append(f"\n> **1**. Go to {tunables('PLEX_REQUEST_URL')}")
    temp.append("\n> **2**. Log in with your __Plex Account__")
    temp.append("\n> **3**. Find a show/movie you want to request")
    temp.append("\n> **4**. Request and wait for the show to download!")
    temp.append("\n")
    temp.append("\nYou can view the status of your requested media through Overseerr.")

    embed = discord.Embed (
        title = f'Plex Requests',
        url=tunables('PLEX_REQUEST_URL'),
        color = PLEX_EMBED_COLOR,
        description=f"{''.join(temp)}"
    )
    embed.set_thumbnail(url="https://www.plex.tv/wp-content/uploads/2018/01/pmp-icon-1.png")
    # embed.set_image(url="https://www.gitbook.com/cdn-cgi/image/height=40,fit=contain,dpr=1,format=auto/https%3A%2F%2F1552750098-files.gitbook.io%2F~%2Ffiles%2Fv0%2Fb%2Fgitbook-legacy-files%2Fo%2Fspaces%252F-MOe2ln-0TTCHnhyqTjc%252Favatar-rectangle-1624155529310.png%3Fgeneration%3D1624155529900251%26alt%3Dmedia")
    embed.set_footer(text="Once downloaded, media will be automatically added to Plex.")
    return embed

def plex_update_1():

    temp = []
    temp.append(
        "• With a combination of [Overseerr](https://overseerr.dev/) and [Plex](https://app.plex.tv/), you can now request media simply by "
        "adding it to your Plex watchlist. At intervals, Overseerr will check your Plex "
        "watchlist and check to see if all the shows on it have been added to Plex. If they "
        "have not, it will add them automatically."
        "\n\n"
        "• This works for all media types: "
        "Movies, TV Shows, Anime, and Anime Movies. All content will be added at the highest "
        "quality available (4K HDR, 4K Dolby Vision, BluRay DualAudio [Multi-Dub] (Anime), etc)."
        "\n"
        #"• Requesting and content discovery is still available on Overseerr and will now __show your Plex "
        #"watch history and recommend content based off of it.__"
    )

    embed = discord.Embed (
        title = f'Plex Update [12/22/22]',
        url=tunables('PLEX_REQUEST_URL'),
        color = GLOBAL_EMBED_COLOR,
        description=f"{''.join(temp)}"
    )
    embed.set_thumbnail(url="https://www.plex.tv/wp-content/uploads/2018/01/pmp-icon-1.png")
    embed.set_image(url="https://support.plex.tv/wp-content/uploads/sites/4/2022/03/Plex-2-800x385.png")
    # embed.set_footer(text="Once downloaded, media will be automatically added to Plex.")
    return embed

async def modified_playtime_embed(u, query, playtime_by_game, sort, limit, updates, scope, offset=0, ptquery=">5m", total=0, avg=0):

    temp = []
    if not scope[0]: temp.append(f":pencil: Name: {u.user.mention}\n")
    elif scope[1].value == "guild": temp.append(f":shield: Guild: **{u.guild}**\n")
    elif scope[1].value == "global": temp.append(":earth_americas: Scope: **Global**\n")
    temp.append(f":mag_right: Search: `{query}`\n")
    detailed = False
    sc = False
    mp = False
    if sort is not None:
        match sort.value:
            case 'lp':
                temp.append("<:ASC_sort:1019497227896500264> Sort: `Least Played`\n")
                mp = True
            case 'ls':
                temp.append("<:DESC_sort:1019497286482538566> Sort: `Longest Session [detailed]`\n")
                detailed = True
            case 'mp':
                temp.append("<:DESC_sort:1019497286482538566> Sort: `Most Played`\n")
                mp = True
            case 'sc':
                temp.append("<:DESC_sort:1019497286482538566> Sort: `Session Count`\n")
                sc = True
            case _:
                temp.append(":clock2: Sort: `Last Played [detailed]`\n")
                detailed = True
    else:
        temp.append(":clock2: Sort: `Last Played [detailed]`\n")
        detailed = True
    temp.append(f":hourglass: Playtime: `{'>5m' if ptquery is None else ptquery}`\n")
    temp.append(":bar_chart: __Search Statistics__:\n")
    temp.append(f"\u200b \u200b├─:stopwatch: Total Playtime: `{time_elapsed(total, 'h')}` | `{round(time_elapsed(total, 'r'), 1)}h`\n")
    temp.append(f"\u200b \u200b└─:chart_with_upwards_trend: Average Session: `{time_elapsed(avg, 'h')}`\n\n")
    
    num = 1
    for i, game in enumerate(playtime_by_game):
        if mp or sc:
            if scope[0] and game[6] == str(u.user.id): temp.append(f":index_pointing_at_the_viewer: ")
            else: temp.append(f"`{i+1+offset}.` ")
        temp.append(f"{game[0]} ")
        if detailed:
            temp.append(f"<t:{game[5]}:R> ")
        else:
            # If not user scope, lookup queryed user
            if scope[0]: temp.append(f"<t:{await last_played(game[6], game[1])}:R> ")
            else: temp.append(f"<t:{await last_played(u.user.id, game[1])}:R> ")
        temp.append(f"**{game[2]}** ")
        if sc:
            temp.append(f"`{game[5]:,} Session")
            if game[5] > 1: temp.append("s`")
            else: temp.append("`")
        elif mp: temp.append(f"`{time_elapsed(game[3], 'h')}` | `{round(time_elapsed(game[3], 'r'), 1)}h`")
        else: temp.append(f"`{time_elapsed(game[3], 'h')}`")

        if scope[0]: temp.append(f" • <@{game[6]}>\n")
        else: temp.append("\n")
        num += 1

    embed = discord.Embed (
        title = "Playtime Search Results",
        color = GLOBAL_EMBED_COLOR,
        description=f"{''.join(temp)}"
    )
    total_sessions = 0
    tot_ses_str = ""
    if sc:
        for count in playtime_by_game:
            total_sessions += count[5]
        if total_sessions > 1: tot_ses_str = f". {total_sessions:,} sessions on this page."
        else: tot_ses_str = f". {total_sessions:,} session on this page."


    if num > limit:
        embed.set_footer(text=f"Showing {(offset + 1):,} - {(offset + limit):,} of {updates:,} results{tot_ses_str}")
    elif updates > 0:
        embed.set_footer(text=f"Showing {(offset + 1):,} - {updates:,} of {updates:,} results{tot_ses_str}")
    else: embed.set_footer(text="Showing 0 - 0 of 0 results")
    if not scope[0]: embed.set_thumbnail(url=await u.user_avatar)
    elif scope[1].value == "guild": embed.set_thumbnail(url=u.guild.icon)
    return embed

def song_search_results(res):
    temp = []
    emojis = [
            "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣",
            "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"
        ]

    temp.append(f"This embed will expire in <t:{int(time.time() + 30)}:R>\n\n")

    temp.append("`[`, `]`, `*`, `_` _removed from titles for formatting purposes_\n")

    tracks = res.tracks
    i = 0
    for track in tracks:
        i += 1
        dur = time_elapsed(int(track.duration / 1000), ":")
        track.title = sanitize_track_name(track)
        temp.append(f"{emojis[i-1]} <:youtube:1031277947463675984> **{track['author']}**: [{track.title}]({track['uri']}) • `{dur}`\n")

        if i >= 10: break


    embed = discord.Embed (
        title = f'Search Results',
        color = GLOBAL_EMBED_COLOR,
        description=f"{''.join(temp)}"
    )

    return embed

def show_playlist_result(res):
    emojis = [
            "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"
    ]
    temp = []
    
    temp.append(f"This embed will expire in <t:{int(time.time() + 30)}:R>\n\n")
    
    temp.append("<a:right_arrow_animated:1011515382672150548> Load YouTube playlist from link?\n\n")
    temp.append("`[`, `]`, `*`, `_` _removed from titles for formatting purposes_\n")
    i = 0
    cnt = len(res.tracks)
    for track in res.tracks:
        i += 1
        dur = time_elapsed(int(track.duration / 1000), ":")
        track.title = sanitize_track_name(track)
        temp.append(f"{emojis[i-1]} <:youtube:1031277947463675984> **{track['author']}**: [{track.title}]({track['uri']}) • `{dur}`\n")
        if i >= 5:
            break
    if cnt > i:
        temp.append(f"\n_+ {cnt - i} more_\n")
    
    embed = discord.Embed (
        title = f'Playlist Found',
        color = GLOBAL_EMBED_COLOR,
        description=f"{''.join(temp)}"
    )
    return embed


async def help_embed(u) -> list:
    
    temp = []
    temp.append(
        f"{u.client.user.mention} help menu. Use `/help <category>` "
        "for a more detailed explaination. "
        "\n\n"
    )

    p = os.getenv('CMD_PREFIX1')
    chat_cmds = []
    if (await u.profile).cmd_enabled('ROLL') == 1: chat_cmds.append(f"**{p}r**, **{p}roll**: :game_die: Roll a number between 0 and 100\n")
    if (await u.profile).cmd_enabled('EIGHT_BALL') == 1: chat_cmds.append(f"**{p}8b**, **{p}8ball**: :8ball: Ask an 8 ball any question\n")
    if (await u.profile).cmd_enabled('COIN_FLIP') == 1: chat_cmds.append(f"**{p}fl**, **{p}flip**: :coin: Flip a coin\n")
    if (await u.profile).cmd_enabled('ANIME_SEARCH') == 1: chat_cmds.append(f"**{p}as**, **{p}anisearch**: <:uwuyummy:958323925803204618> Search for any anime\n")
    if (await u.profile).cmd_enabled('USER_INFO') == 1: chat_cmds.append(f"**{p}s**, **{p}info**: :bar_chart: User Stats/Info\n")
    if len(chat_cmds) > 0:
        temp.append(":speech_balloon: __**Text Commands**__:\n> ")
        temp.append('> '.join(chat_cmds))
        temp.append("\n")

    
    slash_cmds = []
    slash_cmds.append(f"{tunables('SLASH_COMMAND_SUGGEST_HELP')}: :book: Show this help menu\n")
    slash_cmds.append(f"{tunables('SLASH_COMMAND_SUGGEST_SETTINGS')}: :gear: Change {u.client.user.mention} settings (for yourself and {u.guild.name})\n")
    if (await u.profile).cmd_enabled('PLAYTIME') == 1: slash_cmds.append(f"{tunables('SLASH_COMMAND_SUGGEST_PLAYTIME')}: :video_game: Playtime tracking and detailed searching\n")
    if (await u.profile).cmd_enabled('VOICETIME') == 1: slash_cmds.append(f"{tunables('SLASH_COMMAND_SUGGEST_VOICETIME')}: :microphone2: Voicechat tracking and detailed searching\n")
    if (await u.profile).cmd_enabled('POLL') == 1: slash_cmds.append(f"{tunables('SLASH_COMMAND_SUGGEST_POLL')}: :chart_with_upwards_trend: Create a poll lasting up to 24-hours.\n")
    temp.append(":computer: __**Slash Commands**__:\n> ")
    temp.append('> '.join(slash_cmds))


    if (await u.profile).cmd_enabled('PLAY') == 1:
        music_cmds = []
        music_cmds.append(
            "Your guild has been granted access music commands and has "
            "access to all features that come with it. This access includes "
            "YouTube. Because of this, this command will remain private and "
            "restricted to limited guilds.\n\n"
        )
        music_cmds.append(f"{tunables('SLASH_COMMAND_SUGGEST_PLAY')}: :musical_note: Play a song/video from any (soon; YT for now) source.\n")
        music_cmds.append(f"{tunables('SLASH_COMMAND_SUGGEST_STOP')}: :stop_button: Stops playback and disconnects from voice chat\n")
        music_cmds.append(f"{tunables('SLASH_COMMAND_SUGGEST_MUSICCHANNEL')}: :information_source: **Required for all music features**: Set a channel \
                        to be a dedicated music channel. This channel will have a persistent player embed that {u.client.user.mention} \
                        will update. You can skip, pause, stop, control volume, and more with this embed. \
                        Run this command without arguments to deselect the current music channel.\n")
        temp.append("\n:notes: __**Music Player Commands and Info**__:\n")
        temp.append('> '.join(music_cmds))


    if (await u.profile).feature_enabled('THEBOYS_HELP') == 1:
        tb = []
        tb.append(f"{tunables('SLASH_COMMAND_SUGGEST_LEVEL')}: :test_tube: View your level\n")
        tb.append(f"{tunables('SLASH_COMMAND_SUGGEST_TOKENS')}: :coin: View your tokens `[WIP]`\n")
        tb.append(f"{tunables('SLASH_COMMAND_SUGGEST_SHOP')}: :shopping_bags: Token shop `[WIP]`\n")
        temp.append(f"\n:gem: __Commands exclusive to **{u.guild}**__:\n> ")
        temp.append('> '.join(tb))
        
    return temp