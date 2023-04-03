import asyncio
from curses.ascii import isdigit
import discord
from discord.ext import commands
from discord import app_commands
import typing
from Database.GuildObjects import MikoMember
from Voice.Views import VoicetimePageSelector, VoicetimeSearchPageSelector
from Voice.embeds import voicetime_embed, voicetime_search_embed
from Voice.track_voice import avg_voicetime_result, get_average_voice_session, get_total_voice_activity_updates, get_total_voicetime_user, get_total_voicetime_user_guild, total_voicetime_result
from tunables import *
import re
import os
from dotenv import load_dotenv
load_dotenv()

db = AsyncDatabase("VoicetimeCog.py")
        

class VoicetimeCog(commands.Cog):
    def __init__(self, client):
        self.client: discord.Client = client
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.tree = app_commands.CommandTree(self.client)

    @app_commands.command(name="voicetime", description=f"{os.getenv('APP_CMD_PREFIX')}View voicetime for yourself or other people")
    @app_commands.guild_only
    @app_commands.describe(
        user='User to view voicetime (if none specified, will search for yourself)',
        guild='Guild to filter by (Guild name or ID)',
        sort='Choose how to sort search result',
        page_size='How many results to display at once',
        voicetime='Voicetime to sort by: >5m, <5h, all (all results), > is greater than, < is less than. [Session based]',
        scope='Choose level to search on: User level (default) or Guild level',
        query_limit='Change how many total results will be queryed from the database (different than limit)'
    )
    @app_commands.choices(
    sort=[
        app_commands.Choice(name='Most Active', value='ma'),
        app_commands.Choice(name='Least Active', value='la'),
        app_commands.Choice(name='Session Count (by Guild)', value='sc'),
        app_commands.Choice(name='Longest Session (detailed activity list)', value='ls')
    ],
    page_size=[
        app_commands.Choice(name='5 Results', value=5),
        app_commands.Choice(name='10 Results (default)', value=10),
        app_commands.Choice(name='25 Results', value=25)
    ],
    scope=[
        app_commands.Choice(name='User (default)', value="user"),
        app_commands.Choice(name='Guild', value="guild"),
        #app_commands.Choice(name='Global', value="global")
    ],
    query_limit=[
        app_commands.Choice(name='1,000 (default)', value="LIMIT 1000"),
        app_commands.Choice(name='Unlimited (could take up to a minute)', value="")
    ])
    async def vt(self, interaction: discord.Interaction,
                 user: typing.Optional[discord.User] = None,
                 guild: str = None,
                 sort: app_commands.Choice[str] = None,
                 page_size: app_commands.Choice[int] = None,
                 voicetime: str = None,
                 scope: app_commands.Choice[str] = None,
                 query_limit: app_commands.Choice[str] = "LIMIT 1000"
    ):

        await interaction.response.send_message(content=f"Querying database. This may take a few seconds... {tunables('LOADING_EMOJI')}")
        orig_msg = await interaction.original_response()


        if user is None: user = interaction.user
        if sort is not None: sort = sort.value
        if page_size is None: page_size = 10
        else: page_size = page_size.value
        if scope is None: user_scope = True
        elif scope.value != "user": user_scope = False
        else: user_scope = True

        
        # Begin generic voicetime display
        try:
            if guild is None and sort is None and voicetime is None and user_scope:
                tup = await get_total_voice_activity_updates(user_id=user.id)
                avg = await get_average_voice_session(user_id=user.id)
                tot_voicetime = await get_total_voicetime_user(user_id=user.id)
                voicetime_guild = await get_total_voicetime_user_guild(user_id=user.id, server_id=interaction.guild.id)
                if tup > page_size: view = VoicetimePageSelector(client=self.client, user=user, author=interaction.user, page_size=page_size, updates=tup,
                                                                 voicetime=tot_voicetime, avg_session=avg, guild=interaction.guild, voicetime_guild=voicetime_guild)
                else: view = None
                await orig_msg.edit(content=tunables('VOICETIME_CONTENT_MSG'),
                                    embed=await voicetime_embed(
                                        client=self.client,
                                        user=user,
                                        page_size=page_size,
                                        updates=tup,
                                        voicetime=tot_voicetime,
                                        avg_session=avg,
                                        guild=interaction.guild,
                                        voicetime_guild=voicetime_guild
                                    ), view=view)
                return
        except:
            await orig_msg.edit(content=tunables('GENERIC_APP_COMMAND_ERROR_MESSAGE'))
            return

        # End generic voicetime display


        # Begin voicetime query
        sel_cmd = []


        part1 = []
        part1.append("SELECT s.emoji, vt.server_id")
        
        # No sort
        if sort is None: part1.append(", (vt.end_time - vt.start_time) AS total, 0, vt.end_time")

        # Session count
        # Non-detailed response (longest sesh/sesh count) (individual sessions)
        elif sort in ['sc', 'ls']: part1.append(
            ", SUM(vt.end_time - vt.start_time) AS total, AVG(vt.end_time - vt.start_time) AS avg, "
            f"{'COUNT(vt.end_time) AS sc' if sort == 'sc' else 'vt.end_time'}"
            )

        # Most active, least active
        else: part1.append(
            ", SUM(vt.end_time - vt.start_time) AS total, AVG(vt.end_time - vt.start_time) AS avg, 0"
        )
        if not user_scope: part1.append(", vt.user_id")
        sel_cmd.append(''.join(part1))
        del part1 # part1 (sort query) complete



        # Handle voicetime
        part2 = []
        part2.append(
            " FROM VOICE_HISTORY AS vt "
            "INNER JOIN SERVERS AS s ON " ## Only if guild emoji works out
            f"(vt.server_id=s.server_id) "
        )


        all = False
        if voicetime is None: part2.append(f"WHERE (vt.end_time - vt.start_time)>={tunables('THRESHOLD_LIST_VOICE_ACTIVITY')} ")
        elif voicetime.lower() == "all":
            all = True
            part2.append("WHERE ")
        else:
            regex_pt = r"^[<>]\d{1,5}[smhd]{0,1}$|^all$"
            if not re.match(regex_pt, voicetime.lower()):
                await orig_msg.edit(content=f"Error: Invalid playtime entry `{voicetime}`. Examples: `>5m` (greater than 5 minutes), `<5h` (less than 5 hours), `all` returns all results. `<` and `>` are **required**.")
                return
            
            multiplicity = 1
            if not voicetime[len(voicetime) - 1].isdigit():
                match voicetime[len(voicetime) - 1].lower():
                    case 's': pass # No change to multiplicity
                    case 'm': multiplicity = 60
                    case 'h': multiplicity = 3600
                    case 'd': multiplicity = 86400
            
            if voicetime[len(voicetime) - 1].isdigit(): voicetime_val = voicetime[1:]
            else: voicetime_val = voicetime[1:-1]
            
            voicetime_val = multiplicity * int(voicetime_val)
            part2.append(f"WHERE (vt.end_time - vt.start_time){voicetime[0]}{voicetime_val} ")
        ####

        if not all: part2.append("AND ")
        part2.append("vt.end_time is not NULL ")

        # Determine search scope (User or Guild)
        if not user_scope and scope.value == "guild":
            part2.append(f"AND vt.server_id='{interaction.guild.id}' ")
        
        sel_cmd.append(''.join(part2))
        del part2
        ####


        # Handle guild query
        part3 = []
        if str(guild).isdigit() and user_scope:
            guild_obj = self.client.get_guild(int(guild))
            if guild_obj is None:
                await orig_msg.edit(content=f"Could not find any guilds with guild id `{guild}`")
                return
            guild: discord.Guild = guild_obj
            part3.append(f"AND vt.server_id='{guild.id}' ")
        else:

            if guild is not None:
                if guild.startswith('!'): part3.append("AND vt.server_id NOT IN (")
                else: part3.append("AND vt.server_id IN (")

                if guild[1:] == "": guilds = []
                else:
                    guild_sel_cmd = (
                        f"SELECT server_id FROM SERVERS WHERE cached_name LIKE '{'%' + guild + '%'}' LIMIT 10"
                    )
                    guilds = await db.execute(guild_sel_cmd)

                if guilds == []:
                    await orig_msg.edit(content=f"Could not find any guilds matching: `{guild}`")
                    return
                elif type(guilds) == str:
                    guilds = [guilds]

                for i, id in enumerate(guilds):
                    if i == 0:
                        part3.append(f"'{id}'")
                    else:
                        part3.append(f", '{id}'")
                part3.append(") ")


        sel_cmd.append(''.join(part3))

        del part3
        ####

        if user_scope: sel_cmd.append(f"AND vt.user_id='{user.id}' ")

        # Sort query cont.
        part4 = []
        if sort == 'ls':# or not user_scope:
            part4.append(
                "GROUP BY vt.start_time"
                f"{', vt.user_id ' if not user_scope else ' '}"
            )
        elif sort in ['ma', 'la', 'sc']:
            if user_scope: part4.append(
                "GROUP BY vt.server_id"
                f"{'' if not user_scope else ' '}"
            )
            else: part4.append(
                "GROUP BY vt.server_id"
                f"{', vt.user_id ' if not user_scope else ' '}"
            )
        
        
        match sort:
            # Most Active | Longest Session
            case 'ma' | 'ls': part4.append("ORDER BY total DESC ")
            
            # Least Active
            case 'la': part4.append("ORDER BY total ASC ")
            
            # Session Count
            case 'sc': part4.append("ORDER BY sc DESC ")

            # else (unsorted)
            case _: part4.append("ORDER BY end_time DESC ")
        sel_cmd.append(''.join(part4))
        del part4

        sel_cmd.append(query_limit.value if type(query_limit) != str else query_limit)
        ####

        try:
            search_results = await db.execute(exec_cmd=''.join(sel_cmd), p=True)

            if search_results == []:
                msg = []
                msg.append(f"{user} has activity logged, but none with the given search criteria:\n")
                if guild is not None: msg.append(f"`Guild: {guild}`\n")
                if voicetime is not None: msg.append(f"`Voicetime: {voicetime}`")
                if guild is not None or voicetime is not None: msg.append(f"`Scope: {scope}`")
                await orig_msg.edit(content=''.join(msg))
                return
            
            if (guild != interaction.guild and not user_scope and guild is not None) or user != interaction.user and not user_scope:
                ct = "`Guild` or `User` field supplied; omitting due to current scope"
                user = interaction.user
                guild = interaction.guild
            else: ct = tunables('VOICETIME_CONTENT_MSG')
            search_total = total_voicetime_result(search_results)
            search_avg = avg_voicetime_result(search_results)
            if len(search_results) > page_size:
                view = VoicetimeSearchPageSelector(
                    author=interaction.user,
                    user=user,
                    client=self.client,
                    guild=guild,
                    search_results=search_results,
                    sort=sort,
                    page_size=page_size,
                    query=''.join(sel_cmd),
                    results=len(search_results),
                    user_scope=user_scope,
                    vtquery=voicetime,
                    total=search_total,
                    avg=search_avg
                )
            else: view = None

            # Populate guild var with guild object if we only
            # found one guild result
            #if len(guilds) == 1: guild = self.client.get_guild(int(guilds[0]))

            await orig_msg.edit(
                content=ct,
                embed=await voicetime_search_embed(
                    user=user,
                    client=self.client,
                    guild=guild,
                    search_results=search_results[:page_size],
                    sort=sort,
                    page_size=page_size,
                    results=len(search_results),
                    user_scope=user_scope,
                    vtquery=voicetime,
                    total=search_total,
                    avg=search_avg
                ),
                view=view
            )
            return
        except Exception as e:
            print(e)
            await orig_msg.edit(content=tunables('GENERIC_APP_COMMAND_ERROR_MESSAGE'))
        # End voicetime query
        # End voicetime command

        

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        u = MikoMember(user=interaction.user, client=interaction.client)
        await u.ainit()
        if (await u.profile).cmd_enabled('VOICETIME') != 1:
            await interaction.response.send_message(content=tunables('GENERIC_BOT_DISABLED_MESSAGE'), ephemeral=True)
            return False
        
        await u.increment_statistic('VOICETIME_COMMAND')
        return True



async def setup(client: commands.Bot):
    await client.add_cog(VoicetimeCog(client))