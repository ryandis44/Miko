import asyncio
import uuid
import discord
from discord.ext import commands
from Database.database_class import AsyncDatabase
from Presence.GameActivity import GameActivity
from tunables import tunables
from discord.ext.commands import Context
import os
from dotenv import load_dotenv
from Voice.VoiceActivity import VOICE_SESSIONS
from Presence.Objects import PLAYTIME_SESSIONS

from Presence.playtime import find_type_playing, has_app_id, identify_current_application, sesh_id, start_time
from misc.misc import get_user_object
from Database.GuildObjects import MikoMember
from Polls.UI import active_polls
from Music.LavalinkClient import AUDIO_SESSIONS
load_dotenv()

db = AsyncDatabase("cogs.debugger.py")

class Debugger(commands.Cog):
    def __init__(self, client):
        self.client = client

    # Generates a random number between 0 and 100 [inclusive]
    @commands.command(name='debug', aliases=['d'])
    @commands.guild_only()
    async def debugger(self, ctx: Context, *args):
        #if len(ctx.message.mentions) >= 1: user = ctx.message.mentions[0]
        #else: user = ctx.author
        u = MikoMember(user=ctx.author, client=self.client)
        if await u.bot_permission_level <= 4: return
        await u.increment_statistic('DEBUGGER_USED')

        if len(args) == 0:
            await ctx.channel.send(
                f"Please provide something to debug: `{os.getenv('CMD_PREFIX1')}d <category> (user)`\n"
                "Categories: `a` (activity), `gl` (guild list), "
                "`as` (active playtime sessions), `av` (active voice sessions), `po` (active polls) "
                "`music` (active music sessions), `tasks` (all active asyncio tasks), `st` (sticker id in replied msg)"
            )
            return
        
        if len(args) <= 1:
            user = ctx.author
        else:
            user = await get_user_object(self, ctx, args[1])
        
        match args[0].lower():
            case 'a':

                temp = []
                temp.append(f"All current activities: `{user.activities}`\n")

                for i, activity in enumerate(user.activities):
                    cur_playing = find_type_playing(user)
                    if cur_playing[0] and i == cur_playing[1]:
                        game = await identify_current_application(activity, has_app_id(activity))
                    else:
                        game = None
                    st = start_time(activity)
                    temp.append(f"\nActivity `{i+1}`:\n")
                    temp.append(f"> Raw: `{activity}`\n")
                    temp.append(f"> Start time: `{st}` { f'<t:{st}:R>' if st is not None else '' }\n")
                    temp.append(f"> Session ID: `{sesh_id(activity)}`\n")
                    temp.append(f"> Activity Info (Database): `{game}`")
                
                try: pt = PLAYTIME_SESSIONS[user.id]
                except: pt = {'sessions': []}
                for sesh in pt['sessions']:
                    s = pt['sessions'][sesh]
                    s: GameActivity
                    st = s.start_time
                    temp.append("\n")
                    temp.append(f"\n`GameActivity` Object: `{s}`\n")
                    temp.append(f"> User ID: `{s.u.user.id}`\n")
                    temp.append(f"> Start Time: `{st}` { f'<t:{st}:R>' if st is not None else '' }\n")
                    temp.append(f"> Session ID: `{s.session_id}`\n")
                    temp.append(f"> App name/ID: `{s.app.name}`/`{s.app.id}`\n")
                    temp.append(f"> Restored: `{s.restored}`\n")
                    temp.append(f"> Resumed: `{s.is_resumed}` { f'<t:{s.resume_time}:R>' if s.is_resumed else '' }\n")
                    temp.append(f"> Blacklisted ID: `{s.app.blacklisted_id}`\n")

                # If active playtime session, print

                await ctx.channel.send(''.join(temp))
            
            case 'gl':
                
                guilds = self.client.guilds
                temp = []
                temp.append(f"I am in the following guilds (`{len(guilds)}`): ")
                for i, guild in enumerate(guilds):
                    if i == len(guilds) - 1:
                        temp.append(f"`{guild} ({guild.member_count})`")
                    else: temp.append(f"`{guild} ({guild.member_count})`, ")
                await ctx.channel.send(''.join(temp))


            case 'as': # Active playtime sessions
                temp = []
                users = PLAYTIME_SESSIONS.items()
                for user_sessions in users:
                    for i, s in enumerate(user_sessions[1]['sessions']):
                        # 1 is the value of the key value pair of the dict containing all sessions for this user
                        # 'sessions' denotes we want sessions
                        # 's' is the individual session
                        game: GameActivity = user_sessions[1]['sessions'][s]
                        st = game.start_time
                        temp.append(
                            f"\n{game.u.user} (Activity `{i+1}`):\n"
                            f"> User ID: `{game.u.user.id}`\n"
                            f"> Start Time: `{st}` { f'<t:{st}:R>' if st is not None else '' }\n"
                            f"> Session ID: `{game.session_id}`\n"
                            f"> App name/ID: `{game.app.name}`/`{game.app.id}`\n"
                            f"> Restored: `{game.restored}`\n"
                            f"> Resumed: `{game.is_resumed}` { f'<t:{game.resume_time}:R>' if game.is_resumed else '' }\n"
                            f"> Blacklisted ID: `{game.app.blacklisted_id}`\n"
                        )
                await ctx.channel.send(f"`{len(temp)}` active playtime :video_game: sessions")
                await ctx.channel.send(''.join(temp))
            
            case 'va': # Active voice sessions
                temp = []
                sessions = VOICE_SESSIONS.items()
                await ctx.channel.send(f"`{len(sessions)}` active voice :microphone2: sessions")
                await ctx.channel.send(f"{sessions}")
                for key, val in sessions:
                    st = val.start_time
                    user: discord.Member = val.member
                    temp.append(f"\n{user}:\n")
                    temp.append(f"> User ID: `{user.id}`\n")
                    temp.append(f"> Start Time: `{st}` { f'<t:{st}:R>' if st is not None else '' }\n")
                    temp.append(f"> Channel: {user.voice.channel.mention}\n")
                    temp.append(f"> Guild: `{val.guild}`\n")
                    temp.append(f"> Guild ID: `{val.guild.id}`\n")
                await ctx.channel.send(''.join(temp))
            
            case 'hash':
                
                aid = None
                res = None
                while True: # Make sure we do not have duplicate application id
                    aid = uuid.uuid4().hex
                    sel_check_cmd = f"SELECT * FROM APPLICATIONS WHERE app_id='{aid}'"
                    res = await db.execute(sel_check_cmd)
                    if res == []: break
                
                await ctx.channel.send(f"{aid} {res}")
            
            case 'po':

                temp = []
                polls = active_polls.get_all
                print(f"DEBUG REQUESTED 'po': {polls}")
                await ctx.channel.send(f"`{len(polls)}` active polls :bar_chart:")
                for poll in polls:
                    user: discord.Member = poll[0][1].author.user
                    temp.append(f"\n{user}:\n")
                    temp.append(f"> End Time: <t:{poll[0][1].expiration}:R>\n")
                    temp.append(f"> Guild: `{poll[0][1].author.user.guild}`\n")
                    temp.append(f"> Guild ID: `{poll[0][1].author.user.guild.id}`")
                    temp.append(f"> Message Link: [WIP]")
                await ctx.channel.send(''.join(temp))

            case 'music':

                temp = []
                seshs = AUDIO_SESSIONS.items()
                print(f"DEBUG REQUESTED 'music': {seshs}")
                await ctx.channel.send(f"`{len(seshs)}` active music sessions :musical_note:")
                for key, sesh in seshs:
                    user: discord.Member = sesh.original_interaction.user
                    temp.append(f"\n{user} in {user.guild}:\n")
                    temp.append(f"> Player Object: `{sesh.player}`\n")
                    temp.append(f"> Message ID: `{sesh.message}`\n")
                    temp.append(f"> Stopping?: `{sesh.stopping}`")
                await ctx.channel.send(''.join(temp))

            case 'tasks':

                temp = []
                seshs = AUDIO_SESSIONS.items()
                print(f"DEBUG REQUESTED 'music': {asyncio.all_tasks()}")
                await ctx.channel.send(content=f"{asyncio.all_tasks()}")
            
            case 'st':

                if ctx.message.reference is None:
                    await ctx.send(content="Please reply to a message to get sticker id")
                    return

                if ctx.message.reference.resolved.stickers == []:
                    await ctx.send(content="No sticker found")
                    return

                rmsg = ctx.message.reference.resolved
                await ctx.send(
                    content=f"Sticker ID: {rmsg.stickers[0].id}"
                )




async def setup(client: commands.Bot):
    await client.add_cog(Debugger(client))