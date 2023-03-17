import asyncio
import discord
import os
import lavalink
import re
from discord.ext import commands
from discord import app_commands
from Database.GuildObjects import MikoMember
from Database.database_class import Database, ip
from dotenv import load_dotenv
from Music.UI import SongSelectView, PlaylistButtons, show_playlist_result, song_search_results
from Music.PersistentPlayer import PersistentPlayer
from Music.LavalinkClient import AUDIO_SESSIONS
from lavalink import NodeConnectedEvent, NodeDisconnectedEvent
from tunables import *
load_dotenv()

url_rx = re.compile(r'https?://(?:www\.)?.+')

mp = Database("cogs.MusicCog.py")

class MusicCog(commands.Cog):
    def __init__(self, client: discord.Client):
        self.client = client
        self.connect()
    
    def cog_unload(self):
        """ Cog unload handler. This removes any event hooks that were registered. """
        self.client.lavalink._event_hooks.clear()
    
    def connect(self):
        if not hasattr(self.client, 'lavalink'):
            self.client.lavalink = lavalink.Client(self.client.user.id)
            self.client.lavalink.add_event_hooks(self)
        if os.getenv('CONNECTION') != "REMOTE":
            self.client.lavalink.add_node(
                '192.168.0.12',
                2333,
                tunables('LAVALINK_PASSWORD'),
                'na',
                os.getenv('DATABASE')
            )
        else:
            self.client.lavalink.add_node(
                ip,
                2333,
                tunables('LAVALINK_PASSWORD'),
                'na',
                os.getenv('DATABASE')
            )
                
        
        lavalink.add_event_hook(self.track_hook)

    
    @lavalink.listener(NodeConnectedEvent)
    async def on_lavalink_event(self, event):
        print("Lavalink connected")
        print(f"Connected to lavalink {event}")

    @lavalink.listener(NodeDisconnectedEvent)
    async def on_lavalink_disconnect(self, event):
        print("Lavalink disconnected! Attempting to reconnect...")
        print(f"Event: {event}")
        self.connect()
    
    def cog_unload(self): # Predefined in docs
        self.client.lavalink._event_hooks.clear()

    async def cog_command_error(self, interaction: discord.Interaction, error: Exception):
        if isinstance(error, commands.CommandInvokeError):
            await interaction.response.send_message(f"Some error occured: {error.original}", ephemeral=True)

    async def track_hook(self, event):
        if isinstance(event, lavalink.events.QueueEndEvent):
            guild_id = event.player.guild_id
            guild = self.client.get_guild(guild_id)
            try: sesh = AUDIO_SESSIONS[guild.id]
            except: sesh = None
            if sesh is None: return
            await sesh.stop(end=True)
        
        # if isinstance(event, lavalink.events.TrackStartEvent):
        #     sesh = audio_sessions.get_val(int(event.player.guild_id))
        #     if sesh is None: return
        #     await sesh.add_history(event.track)
        
        # Used to update timestamp on embed
        if isinstance(event, lavalink.events.PlayerUpdateEvent):
            if event.position is None: return
            try: sesh = AUDIO_SESSIONS[int(event.player.guild_id)]
            except: sesh = None
            if sesh is None: return
            await sesh.refresh_timestamp(event.position / 1000)

    @commands.Cog.listener()
    async def on_ready(self):
        self.tree = app_commands.CommandTree(self.client)

    @app_commands.command(name="play", description=f"{os.getenv('APP_CMD_PREFIX')}Play a video or song from YouTube (other services to come)")
    @app_commands.guild_only
    @app_commands.describe(
        search='Song/Playlist name/link'
    )
    async def play_song(self, interaction: discord.Interaction, *, search: str):
        msg = await interaction.original_response()
        afk = interaction.guild.afk_channel
        if interaction.user.voice is None:
            await msg.edit(content="You must be in a voice channel to use this command.")
            await asyncio.sleep(tunables('QUICK_EPHEMERAL_DELETE_AFTER'))
            try: await msg.delete()
            except: pass
            return
        elif afk is not None and interaction.user.voice.channel.id == afk.id:
            await msg.edit(
                content="You must be in a channel other than this guild's AFK channel to use this command."
            )
            await asyncio.sleep(tunables('QUICK_EPHEMERAL_DELETE_AFTER'))
            try: await msg.delete()
            except: pass
            return
        
        u = MikoMember(
            user=interaction.user,
            client=interaction.client,
            check_exists=False
        )
        
        attempt = 0
        while True:
            try:
                attempt += 1
                

                player = interaction.client.lavalink.player_manager.create(interaction.guild.id)
                original_search = search
                search = search.strip('<>')

                if not url_rx.match(search):
                    search = f'ytsearch:{search}'
                results: lavalink.LoadResult = await player.node.get_tracks(search)

                match results.load_type:

                    case 'TRACK_LOADED':
                        try: sesh = AUDIO_SESSIONS[interaction.guild.id]
                        except:
                            pp = PersistentPlayer(original_interaction=interaction)
                            await pp.ainit()
                            AUDIO_SESSIONS[interaction.guild.id] = pp
                            sesh = AUDIO_SESSIONS[interaction.guild.id]
                        
                        if await u.music_channel is None:
                            ad = f"\n\n{tunables('MUSIC_BOT_MUSIC_CHANNEL_AD')}"
                        else: ad = ""
                        await sesh.play(tracks=results.tracks[0], requester=interaction.user.id)
                        await msg.edit(
                            content=(
                                f"Added `{results.tracks[0]['title']}` by `{results.tracks[0]['author']}` to queue.{ad}"
                            )
                        )
                        mc = await u.music_channel
                        if mc is not None:
                            await mc.send(
                                content=f"🎵 {interaction.user.mention} added `{results.tracks[0].title}` by `{results.tracks[0].author}` to the queue.",
                                allowed_mentions=discord.AllowedMentions(users=False)
                                )
                        await asyncio.sleep(tunables('QUICK_EPHEMERAL_DELETE_AFTER'))
                        try: await msg.delete()
                        except: pass
                        return
                    
                    case 'PLAYLIST_LOADED':
                        view=PlaylistButtons(
                            original_interaction=interaction,
                            results=results
                        )
                        await msg.edit(embed=show_playlist_result(results=results), view=view, content=None)
                        return
                
                if len(results.tracks) == 0:
                    await msg.edit(content=f"No results found for `{original_search}`")
                    await asyncio.sleep(tunables('QUICK_EPHEMERAL_DELETE_AFTER'))
                    try: await msg.delete()
                    except: pass
                    return

                view=SongSelectView(
                    original_interaction=interaction,
                    results=results
                )
                await msg.edit(embed=song_search_results(results=results), view=view, content=None)                
  
                
                break
            except Exception as e:
                if attempt == 1:
                    await msg.edit(
                        content=f"Connection to music server was lost, reconnecting... {tunables('LOADING_EMOJI')}"
                    )
                self.connect()
                await asyncio.sleep(1)
                if attempt >= 5:
                    await msg.edit(
                        content=f"Something went wrong: {e}"
                    )
                    break
        
    
    @app_commands.command(name="stop", description=f"{os.getenv('APP_CMD_PREFIX')}Stops playing audio and disconnects bot from voice chat.")
    @app_commands.guild_only
    async def stop_song(self, interaction: discord.Interaction):
        msg = await interaction.original_response()
        u = MikoMember(user=interaction.user, client=interaction.client, check_exists=False)
        vc = interaction.guild.voice_client
        if vc is None:
            await msg.edit(content="I am not in any voice channels in this guild.")
            return

        try: sesh = AUDIO_SESSIONS[interaction.guild.id]
        except: sesh = None
        if sesh is not None:
            val = await sesh.stop(interaction=interaction)
        else: val = True

        if not val:
            await msg.edit(
                content=tunables('MUSIC_BOT_NOT_IN_SAME_VOICE_CHANNEL')
            )
            await asyncio.sleep(tunables('QUICK_EPHEMERAL_DELETE_AFTER'))
            await msg.delete()
            return
        
        mc = await u.music_channel
        if mc is None:
            await msg.edit(
                content=(
                    f"⏹ Disconnected from `{vc.channel}`\n\n"
                    f"{tunables('MUSIC_BOT_MUSIC_CHANNEL_AD')}"
                )
            )
            return

        if mc.id == interaction.channel.id:
            await interaction.channel.send(
                content=f"⏹ {interaction.user.mention} disconnected me from `{vc.channel}` with </stop:1045078654323007613>",
                allowed_mentions=discord.AllowedMentions(users=False)
            )
            try: await msg.delete()
            except: pass
            return
        
        try: await msg.edit(content=f"⏹ Disconnected from `{vc.channel}`")
        except: pass
        await mc.send(
            content=f"⏹ {interaction.user.mention} disconnected me from `{vc.channel}` with </stop:1045078654323007613>",
            allowed_mentions=discord.AllowedMentions(users=False)
        )
        
        await asyncio.sleep(tunables('QUICK_EPHEMERAL_DELETE_AFTER'))
        try: await msg.delete()
        except: pass

    @app_commands.command(name="musicchannel", description=f"{os.getenv('APP_CMD_PREFIX')}Set guild music channel (admin only)")
    @app_commands.guild_only
    async def set_music_channel(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        msg = await interaction.original_response()
        u = MikoMember(user=interaction.user, client=interaction.client, check_exists=False)

        if not interaction.user.guild_permissions.manage_channels and await u.bot_permission_level <= 3:
            await msg.edit(content="You must have `Manage Channels` permission to set music channel.")
            return

        if channel is None:
            upd_cmd = f"UPDATE SERVERS SET music_channel=NULL WHERE server_id='{interaction.guild.id}'"
            mp.db_executor(upd_cmd)
            await msg.edit(content=f"Successfully removed music channel from **{interaction.guild}**")
            return

        upd_cmd = f"UPDATE SERVERS SET music_channel='{channel.id}' WHERE server_id='{interaction.guild.id}'"
        mp.db_executor(upd_cmd)
        await msg.edit(content=f"Set **{interaction.guild}** music channel to {channel.mention}\nRun the command again without arguments to unset channel.")

    

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        u = MikoMember(user=interaction.user, client=interaction.client)
        await u.ainit()

        if not tunables('COMMAND_ENABLED_PLAY'):
            await interaction.response.send_message(content=tunables('COMMAND_DISABLED_MESSAGE'), ephemeral=True)
            return False

        if not (await u.profile).cmd_enabled('PLAY'):
            await interaction.response.send_message(content=tunables('MUSIC_BOT_NO_PRIVLEDGES'), ephemeral=True)
            return False
        
        
        await interaction.response.send_message(
            content=tunables('LOADING_EMOJI'),
            ephemeral=True
        )
        return True

async def setup(client: commands.Bot):
    await client.add_cog(MusicCog(client))