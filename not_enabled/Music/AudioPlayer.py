import asyncio
import functools
import discord
import os
from discord.ext import commands
from discord import app_commands
from Database.GuildObjects import MikoMember
from utils.HashTable import HashTable

voice_sessions = HashTable(10000)

class YTDLError(Exception):
    pass

class AudioPlayerrr(commands.Cog):
    def __init__(self, client):
        self.client = client
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.tree = app_commands.CommandTree(self.client)

    @app_commands.command(name="sound", description=f"{os.getenv('APP_CMD_PREFIX')}Play a video or song from YouTube or Spotify")
    @app_commands.guild_only
    @app_commands.describe(
        search='Song link/name'
    )
    async def play_sound(self, interaction: discord.Interaction, *, search: str):
        global voice_sessions
        
        u = MikoMember(user=interaction.user, client=interaction.client)
        if await u.status == "inactive":
            await interaction.response.send_message("This bot has been disabled in this guild.", ephemeral=True)
            return

        
        if interaction.user.voice is None:
            await interaction.response.send_message(f"You must be in a voice channel to play audio", ephemeral=True)
            return

        

        async with interaction.channel.typing():
            voice_session = voice_sessions.get_val(interaction.guild.id)
            if voice_session is None:
                voice_sessions.set_val(interaction.guild.id, await Music.create(interaction, self.client))
            else:
                await interaction.response.send_message("Already connected", ephemeral=True)
                #await voice_session.play_hector()
                resp = await voice_session.play(search)
                print(f"Returned: {resp}")
                #self.vo
                

        
        vc = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client
        if voice_client is not None and voice_client.channel != vc:
            await voice_client.disconnect()
            voice_client.cleanup()
            await vc.connect()

        
        if voice_client is None:
            voice_client = await vc.connect()


        
        #async with interaction.channel.typing():
        #    await interaction.response.defer()
        #    try:
        #        print("test0")
        #        source = await YTDLSource.create_source(interaction, search, loop=self.client.loop)
        #        print("test0.5")
        #    except YTDLError as e:
        #        await interaction.response.send_message(f'An error occurred while processing this request: {e}', ephemeral=True)
        #    else:
        #        song = Song(source)
        #        
        #        await interaction.voice_state.songs.put(song)
        #        await interaction.followup.send(f"{source} + {song}", embed=song.create_embed())
                
        ffmpeg = os.path.abspath("ffmpeg/bin/ffmpeg.exe")
                # voice_client.play(discord.FFmpegPCMAudio(
                    # executable=ffmpeg,
                    # source=song)
                # )
                #await interaction.response.send_message('Enqueued {}'.format(str(source)))




        
        #file = os.path.abspath("not_enabled/Music/hector_likes_kids.mp3")
        file = os.path.abspath("not_enabled/Music/theme.mp3")
        #file = os.path.abspath(await YTDLSource.from_url(search, loop=self.client.loop))
        voice_client.play(discord.FFmpegPCMAudio(
            executable=ffmpeg,
            source=file)
            )
        
        while voice_client.is_playing():
            await asyncio.sleep(0.5)
        await voice_client.disconnect()
        voice_client.cleanup()






class Music():
    @classmethod
    async def create(self, interaction: discord.Interaction, client: discord.Client):
        print("Music class created.")
        self.client = client
        self.user = interaction.user
        self.guild = interaction.guild
        self.channel = interaction.channel
        self.voice_channel = interaction.user.voice.channel
        self.interaction = interaction
        self.voice_client = await self.prepare_voice_client(self)
        await self.interaction.response.send_message("test", ephemeral=True)
        return self
    
    async def prepare_voice_client(self):
        # Get the voice client object (if there is one)
        vc = self.guild.voice_client

        # Connect to the voice channel if not connected to any vc
        # in self.guild
        if vc is None: return await self.voice_channel.connect()

        # If already in another vc in self.guild, disconnect from
        # that channel and switch to self.voice_channel
        elif vc is not None and self.voice_channel != vc.channel:
            await vc.disconnect()
            vc.cleanup()
            return await self.voice_channel.connect()

    def print_sum():
        print("hi")    

    @classmethod
    async def play_hector(self):
        print("Playing...")
        ffmpeg = os.path.abspath("ffmpeg/bin/ffmpeg.exe")
        file = os.path.abspath("Music/IMG_7712.mov")
        #file = os.path.abspath(await YTDLSource.from_url(search, loop=self.client.loop))
        self.voice_client.play(discord.FFmpegPCMAudio(
            executable=ffmpeg,
            source=file)
            )
        while self.voice_client.is_playing():
            await asyncio.sleep(0.5)
        voice_sessions.delete_val(self.guild.id)
        await self.voice_client.disconnect()
        await self.channel.send("Queue complete. Disconnecting.")
        del self




async def setup(client: commands.Bot):
    await client.add_cog(AudioPlayerrr(client))