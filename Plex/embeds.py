import time
import discord
from tunables import *
from Database.GuildObjects import MikoMember
from pyarr import SonarrAPI
from Plex.background import day_to_int, int_to_weekday, this_week, utc_to_central
import os
from dotenv import load_dotenv
from datetime import datetime
load_dotenv()

def sonarr():
    if os.getenv('CONNECTION') == "REMOTE":
        host_url = tunables('SONARR_URL')
    else:
        host_url = 'http://192.168.0.12:8989/'
    api_key = tunables('SONARR_API_KEY')
    s = SonarrAPI(host_url=host_url, api_key=api_key)
    return s

def plex_upcoming(day: list) -> discord.Embed:

    temp = []
    prev_day = -1
    weekday = None
    for i, show in enumerate(day):

        # print(f"{show['series']['title']} {i} {len(day)}")
        # print(show)
        # print("\n")
        
        air_time = utc_to_central(show['airDateUtc'])
        if prev_day != air_time.weekday():
            prev_day = air_time.weekday()
            day_ts = day_to_int(air_time)
            weekday = int_to_weekday(prev_day)
            temp.append(f"\n\n__**{weekday}**__┊__<t:{day_ts}:D>__ [{len(day)} total]:\n")

        try: season = show['seasonNumber']
        except: season = 1
        try: episode = show['episodeNumber']
        except: episode = 1
        try: ab_episode = show['absoluteEpisodeNumber']
        except: ab_episode = None

        temp.append(
                f"> • <t:{int(air_time.timestamp())}:R> [{show['series']['title']}](https://app.plex.tv/):"
                f"『`{show['title']}`』"
                f"S{season:,} E{episode:,}{'' if ab_episode is None else f' ({ab_episode:,})'}"
            )

        if i+1 != len(day): temp.append("\n> ")
        temp.append("\n")

    embed = discord.Embed (
        title = f'Upcoming this week on Plex [{weekday}]',
        url="https://app.plex.tv/",
        color = PLEX_EMBED_COLOR,
        description=f"{''.join(temp)}"
    )
    embed.set_thumbnail(url="https://www.plex.tv/wp-content/uploads/2018/01/pmp-icon-1.png")
    embed.set_footer(text=f"All dates and times in US Central Time")
    return embed


def plex_multi_embed() -> list:
    s = sonarr()
    start, end = this_week()
    cal = s.get_calendar(unmonitored=False, start_date=start, end_date=end)

    embeds = []
    day_start = 0
    prev_day = -1
    for i, show in enumerate(cal):

        # print(f"{show['series']['title']} {i} {len(cal)}")
        # print(show)
        # print("\n")

        air_time = utc_to_central(show['airDateUtc'])
        if prev_day == -1:
            prev_day = air_time.weekday()

        if prev_day != air_time.weekday() or i+1 == len(cal):
            prev_day = air_time.weekday()
            e = plex_upcoming(cal[day_start:i if i+1 != len(cal) else i+1])
            if e.description != "": embeds.append(e)
            day_start = i
        
    return embeds




def info_quality() -> discord.Embed:
    temp = []

    #[Plex Help Article](https://support.plex.tv/articles/115007570148-automatically-adjust-quality-when-streaming/), 
    temp.append(
            "Plex automatically sets your streaming quality very low. This setting is per device and needs to be set once per "
            "new device or browser. Changing quality is easy:\n\n"
            "> **1**. Go to `Settings` (on Web/PC it is the wrench in the top right)\n> \n"
            "> **2**. Go to `Video Quality` (Quality on some devices)\n> \n"
            "> **3**. Set `Remote Streaming` (`Internet Streaming` on some devices) to whatever quality you "
            "want to stream in.\n> \n"
            "> **4**. Optional (recommended): `Turn on Automatically Adjust Quality`. If the connection between you and Plex "
            "is unstable (on your end or Plex), this will adjust quality similar to YouTube.\n> \n"
            "> **5**. **Note**: If streaming on mobile, set `Limit Cellular Data` to `off` or your quality settings will not "
            "apply if you are not on WiFi.\n> \n"
            "> **6**. `Save Changes` (auto saves on some devices)\n"
            "\n"
            "A more in-depth explanation is available on this "
            "[Plex Help Article](https://support.plex.tv/articles/115007570148-automatically-adjust-quality-when-streaming/)"
        )

    embed = discord.Embed (
        title = f'Video Quality Info',
        color = PLEX_EMBED_COLOR,
        description=f"{''.join(temp)}"
    )
    embed.set_thumbnail(url="https://www.plex.tv/wp-content/uploads/2018/01/pmp-icon-1.png")
    embed.set_image(url="attachment://quality.png")
    return embed

def info_anime() -> discord.Embed:
    temp = []

    temp.append(
            "For anime, you have to tell Plex whether you want to watch anime subbed or dubbed. "
            "Unlike quality settings, this setting only needs to be set once per account (can be "
            "changed as much as wanted). These settings will tell Plex to select your desired "
            "audio language and subtitles (for both Subbed and Dubbed).\n\n"
            
            "Scroll down to find Subbed and Dubbed settings."
        )

    embed = discord.Embed (
        title = f'Audio and Subtitle Settings',
        color = PLEX_EMBED_COLOR,
        description=f"{''.join(temp)}"
    )
    embed.set_thumbnail(url="https://www.plex.tv/wp-content/uploads/2018/01/pmp-icon-1.png")
    return embed

def info_subbed() -> discord.Embed:
    temp = []

    temp.append(
            "Subbed:\n\n"
            "> **1**. Go to [Plex Web](https://app.plex.tv) on any device\n> \n"
            "> **2**. Go to `Settings` (wrench in top right)\n> \n"
            "> **3**. Go to `Account` (top of left menu bar)\n> \n"
            "> **4**. Find `Audio & Subtitle Settings`\n> \n"
            "> **5**. Enable `Automatically select audio and subtitle tracks`\n> \n"
            "> **6**. Set `Preferred Audio Language` to **日本語** (at the bottom)\n> \n"
            "> **7**. Set `Preferred Subtitle Language` to **English**\n> \n"
            "> **8**. Set `Auto Select Subtitle Mode` to **Shown with foreign audio**\n> \n"
            "> **9**. For the last two: `Prefer non-SDH subtitles` and `Prefer forced subtitles`\n> \n"
            "> **10**. Save changes."
        )

    embed = discord.Embed (
        title = f'[SUBBED] How to Select Subbed for Anime',
        color = PLEX_EMBED_COLOR,
        description=f"{''.join(temp)}"
    )
    embed.set_thumbnail(url="https://www.plex.tv/wp-content/uploads/2018/01/pmp-icon-1.png")
    embed.set_image(url="attachment://subbed.png")
    return embed

def info_dubbed() -> discord.Embed:
    temp = []

    temp.append(
            "Dubbed:\n\n"
            "> **1**. Go to [Plex Web](https://app.plex.tv) on any device\n> \n"
            "> **2**. Go to `Settings` (wrench in top right)\n> \n"
            "> **3**. Go to `Account` (top of left menu bar)\n> \n"
            "> **4**. Find `Audio & Subtitle Settings`\n> \n"
            "> **5**. Enable `Automatically select audio and subtitle tracks`\n> \n"
            "> **6**. Set `Preferred Audio Language` to **English**\n> \n"
            "> **7**. Set `Preferred Subtitle Language` to **English**\n> \n"
            "> **8**. Set `Auto Select Subtitle Mode` to **Shown with foreign audio**\n> \n"
            "> **9**. For the last two: `Prefer non-SDH subtitles` and `Prefer forced subtitles`\n> \n"
            "> **10**. Save changes."
        )

    embed = discord.Embed (
        title = f'[DUBBED] How to Select Dubbed for Anime',
        color = PLEX_EMBED_COLOR,
        description=f"{''.join(temp)}"
    )
    embed.set_thumbnail(url="https://www.plex.tv/wp-content/uploads/2018/01/pmp-icon-1.png")
    embed.set_image(url="attachment://dubbed.png")
    return embed




def plex_update_2_2() -> discord.Embed:

    temp = []

    temp.append(
            "• New episodes are already added to Plex as they release with the help of [Sonarr](https://sonarr.tv), "
            "and now with a combination of <@1017998983886545068> and the Sonarr API, a weekly Plex release calendar "
            "is now available on Discord. This calendar will be posted weekly automatically at midnight (CST) "
            "every Sunday in the <#936495210387619861> channel.\n\n"
            
            "• The calendar automatically posted in <#936495210387619861> only updates once a week when it is "
            "sent. However, you can check a realtime version (i.e. new show(s) added to Plex) anytime using `/plex calendar`"
        )

    embed = discord.Embed (
        title = f'Plex Mini-Update [1/3/23]',
        url="https://app.plex.tv/",
        color = GLOBAL_EMBED_COLOR,
        description=f"{''.join(temp)}"
    )
    embed.set_thumbnail(url="https://www.plex.tv/wp-content/uploads/2018/01/pmp-icon-1.png")
    return embed

def plex_update_2_3() -> discord.Embed:

    temp = []

    temp.append(
            "A few help channels have been made to make it easier to navigate Plex "
            "and to ensure you have your settings correct. Information on **streaming "
            "quality**, **requesting**, and more is available in <#1061375584300699668>"
        )

    embed = discord.Embed (
        title = f'Plex Mini-Update [1/10/23]',
        url="https://app.plex.tv/",
        color = PLEX_EMBED_COLOR,
        description=f"{''.join(temp)}"
    )
    embed.set_thumbnail(url="https://www.plex.tv/wp-content/uploads/2018/01/pmp-icon-1.png")
    return embed

def plex_update_2_28_23() -> discord.Embed:

    temp = []

    temp.append(
            "> **New!** Popular content on Plex will now be shown on Home "
            "(must have each library pinned [shown in image; might have to zoom in]) and will show "
            "the most watched content from the last month (updates nightly). The "
            "item in the #1 (leftmost) slot is the most popular for the last month, and so on."
            "\n> \n"
            "> **Requests Language Changes**: Media was set to download in English only (except Anime). "
            "This has been changed to allow any language to be downloaded (except Anime), but "
            "with a preference on English, allowing for movies with native languages other "
            "than English to download in their original language with subtitles and/or an "
            "English Dub option."
        )

    embed = discord.Embed (
        title = f'Plex Mini-Update [2/28/23]',
        url="https://app.plex.tv/",
        color = PLEX_EMBED_COLOR,
        description=f"{''.join(temp)}"
    )
    embed.set_thumbnail(url="https://www.plex.tv/wp-content/uploads/2018/01/pmp-icon-1.png")
    embed.set_image(url="attachment://popular_info.png")
    return embed