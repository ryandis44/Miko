import asyncio
import time
import discord
from discord.ext import commands
import lavalink
from misc.misc import time_elapsed
from tunables import *
from Music.LavalinkClient import AUDIO_SESSIONS, ensure_voice
from Database.GuildObjects import MikoMember


'''
This file is responsible for maintaining active audio sessions and,
if applicable, refreshing and maintaining the embed with current
player statistics (PersistentPlayer).

This file also handles the button interactions and volume control,
as well dealing with abuse (i.e. changing player settings without
being in the voice channel with the bot).
'''

class PersistentPlayer():

    def __init__(self, original_interaction: discord.Interaction):
        self.u = MikoMember(user=original_interaction.user, client=original_interaction.client, check_exists=False)
        self.original_interaction = original_interaction
        self.player: lavalink.DefaultPlayer = original_interaction.client.lavalink.player_manager.create(original_interaction.guild.id)
        self.__elapsed_timestamp = "0:00:00"
        self.__elapsed = 0
        self.stopping = False
        self.__repositioning = False
        self.message: discord.Message = None
        self.view = PlayerButtons(pp=self)
    
    async def ainit(self):
        await self.__embed()
        self.__channel = await self.u.music_channel

    async def __embed(self):
        temp = []
        i = 0
        cnt = len(self.player.queue)

        if self.player.current is None:
            self.embed = None
            return
        
        dur = time_elapsed(int(self.player.current.duration / 1000), ':')
        temp.append(f"\u200b \u200b├─ Title: `{self.player.current.title}`\n")
        temp.append(f"\u200b \u200b├─ By: `{self.player.current.author}`\n")
        temp.append(f"\u200b \u200b├─ Timestamp: `{self.__elapsed_timestamp} / {dur}`\n")
        temp.append(f"\u200b \u200b└─ Source: <:youtube:1031277947463675984> [YouTube]({self.player.current.uri})\n")

        if self.player.queue == []:
           temp.append("\n`Queue is empty`\n")
        else:
            total_milliseconds = 0
            for track in self.player.queue:
                total_milliseconds += track.duration
            total_milliseconds += (self.player.current.duration - self.player.position)
            total_time = time_elapsed(int(total_milliseconds / 1000), "h")
            temp.append(f":stopwatch: Total Queue Time: `{total_time}`\n\n")

            temp.append("**Up Next**\n")
            for track in self.player.queue:
                i += 1
                dur = time_elapsed(int(track.duration / 1000), ":")
                temp.append(
                    f"<:youtube:1031277947463675984> [{track.title}]({track.uri}) • <@{track.requester}> • `{dur}`\n"
                )
                if i >= 5: break
            
            if cnt > i:
                temp.append(f"_**+{cnt - i} more**_")
            
        u = MikoMember(
            user=self.original_interaction.guild.get_member(self.player.current.requester),
            client=self.original_interaction.client,
            check_exists=False
        )
        embed = discord.Embed(
            title=":musical_note: Now Playing",
            color = GLOBAL_EMBED_COLOR,
            description=f"{''.join(temp)}"
        )
        embed.set_footer(text="This embed will update automatically.")
        embed.set_thumbnail(url=self.original_interaction.guild.icon)
        embed.set_author(name=f"Requested by {await u.username}", icon_url=await u.user_avatar)
        self.embed = embed

    async def __enqueue(self, tracks, requester: int):
        await ensure_voice(interaction=self.original_interaction)
        if type(tracks) == list:
            for track in tracks:
                self.player.add(track=track, requester=requester)
                await self.u.increment_statistic('MUSICBOT_TRACKS_QUEUED')
        else:
            self.player.add(track=tracks, requester=requester)
            await self.u.increment_statistic('MUSICBOT_TRACKS_QUEUED')
        if not self.player.is_playing: await self.player.play()

    async def play(self, tracks, requester: int):
        await self.__enqueue(
            tracks=tracks,
            requester=requester
        )
        await self.__update_embed()
    
    async def skip(self):
        await self.player.skip()
        await self.__update_embed()
    
    async def stop(self, interaction: discord.Interaction = None, end: bool=False) -> bool:

        if interaction is not None:
            if interaction.user.voice is None: return False
            elif interaction.user.voice.channel.id != interaction.guild.voice_client.channel.id: return False

        if self.stopping: return False
        self.stopping = True
        vc = self.original_interaction.guild.voice_client
        if vc is not None:
            await vc.disconnect(force=True)
            vc.cleanup()
        
        await self.player.set_volume(100) # Maintain default volume of 100 on creation of new player
        await self.player.stop()          # in this guild
        self.player.queue = []
        await self.__delete(interaction=interaction, end=end)
        return True
    
    async def __delete(self, interaction: discord.Interaction, end: bool):
        if interaction is None:
            if end: msg = "Queue complete."
            else:
                msg = "Playback ended because I was disconnected from voice chat."
        else:
            u = MikoMember(user=interaction.user, client=interaction.client, check_exists=False)
            await u.increment_statistic('MUSICBOT_SESSIONS_ENDED')
            msg = f"{await u.username} ended playback"


        embed = discord.Embed(
            color = GLOBAL_EMBED_COLOR,
            description="Use </play:1045078654323007612> to play more music."
        )
        embed.set_author(
            name=msg,
            icon_url= None if interaction is None else await u.user_avatar
        )
        await asyncio.sleep(1) # ensure __update_embed() does not overwrite new embed
        if self.message is not None: await self.message.edit(embed=embed, view=None)
        try: del AUDIO_SESSIONS[self.original_interaction.guild.id]
        except: pass
        del self
    
    async def toggle_pause(self):
        await self.player.set_pause(not self.player.paused)
        await self.__update_embed()
    
    async def reposition(self):
        if self.__repositioning or self.message is None: return
        self.__repositioning = True
        if int(self.message.created_at.timestamp()) >= int(time.time()) - 5:

            '''
            We wait 5 seconds after the last embed was sent to ensure we are
            not hitting the discord rate limit. This also helps mitigate
            duplicate embeds.
            '''
            await asyncio.sleep(5)
            if self.stopping: return
        try: await self.message.delete()
        except: pass
        self.message = None
        await self.__process_embed()
        self.__repositioning = False
        return
    
    async def refresh_timestamp(self, elapsed):
        if self.__elapsed == elapsed or self.stopping: return
        self.__elapsed = elapsed
        self.__elapsed_timestamp = time_elapsed(int(self.__elapsed), ":")
        await self.__update_embed()

    async def __update_embed(self):
        if self.stopping: return
        await self.__embed()
        await self.__process_embed()
    
    async def __process_embed(self):
        if self.__channel is None: return
        if self.message is None:
            self.message = await self.__channel.send(
                embed=self.embed,
                view=self.view
            )
            await self.view.refresh_view()
        else:
            try:
                await self.message.edit(
                    embed=self.embed,
                    view=self.view
                )
                await self.view.refresh_view()
            except: pass


class PlayerButtons(discord.ui.View):
    def __init__(self, pp: PersistentPlayer) -> None:
        super().__init__(timeout=None)
        self.pp = pp
        self.add_item(
            VolumeDropdown(
                pp=pp
            )
        )

    async def refresh_view(self):
        self.__button_presence()
        try: await self.pp.message.edit(view=self)
        except: pass
    
    def __button_presence(self):
        pause = [x for x in self.children if x.custom_id=="pause_song"][0]
        stop = [x for x in self.children if x.custom_id=="stop_song"][0]
        resume = [x for x in self.children if x.custom_id=="resume_song"][0]
        next = [x for x in self.children if x.custom_id=="next_song"][0]
        vol = [x for x in self.children if x.custom_id=="volume"][0]

        stop.disabled = False
        pause.disabled = self.pp.player.paused
        resume.disabled = not self.pp.player.paused
        next.disabled = True if self.pp.player.queue == [] else False
        vol.disabled = False

    
    @discord.ui.button(style=discord.ButtonStyle.primary, emoji="⏸", custom_id="pause_song", disabled=True, row=2)
    async def pause_callback(self, interaction: discord.Interaction, button = discord.Button):
        await interaction.response.edit_message()
        await self.pp.toggle_pause()
        await self.pp.u.increment_statistic('MUSICBOT_PAUSE_BUTTONS_PRESSED')

    # Not processing stop button in __button_presence because it is always enabled
    @discord.ui.button(style=discord.ButtonStyle.red, emoji="⏹", custom_id="stop_song", disabled=True, row=2)
    async def stop_callback(self, interaction: discord.Interaction, button = discord.Button):
        await self.pp.stop(interaction=interaction)

    @discord.ui.button(style=discord.ButtonStyle.primary, emoji="▶", custom_id="resume_song", disabled=True, row=2)
    async def resume_callback(self, interaction: discord.Interaction, button = discord.Button):
        await interaction.response.edit_message()
        await self.pp.toggle_pause()
        await self.pp.u.increment_statistic('MUSICBOT_PLAY_BUTTONS_PRESSED')

    @discord.ui.button(style=discord.ButtonStyle.success, emoji="⏭", custom_id="next_song", disabled=True, row=2)
    async def next_song_callback(self, interaction: discord.Interaction, button = discord.Button):
        await interaction.response.edit_message()
        await self.pp.skip()
        await self.pp.u.increment_statistic('MUSICBOT_TRACKS_SKIPPED')

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.voice is None or interaction.user.voice.channel.id != \
            interaction.guild.voice_client.channel.id:
            await interaction.response.send_message(
                content=tunables('MUSIC_BOT_NOT_IN_SAME_VOICE_CHANNEL'),
                ephemeral=True
            )
            return False
        return True


class VolumeDropdown(discord.ui.Select):
    def __init__(self, pp: PersistentPlayer):
        self.pp = pp
        self.red_warning = self.pp.original_interaction.client.get_emoji(1074463168526561311)

        options = []
        options.append(
            discord.SelectOption(
                label="25%",
                description="Set volume to 25%",
                value=25,
                emoji="🔈"
            )
        )
        options.append(
            discord.SelectOption(
                label="50%",
                description="Set volume to 50%",
                value=50,
                emoji="🔉"
            )
        )
        options.append(
            discord.SelectOption(
                label="75%",
                description="Set volume to 75%",
                value=75,
                emoji="🔉"
            )
        )
        options.append(
            discord.SelectOption(
                label="100%",
                description="Set volume to 100%",
                value=100,
                emoji="🔊"
            )
        )
        options.append(
            discord.SelectOption(
                label="200%",
                description="Set volume to 200%. Some audio is distorted.",
                value=200,
                emoji="🔊"
            )
        )
        options.append(
            discord.SelectOption(
                label="300%",
                description="Set volume to 300%. More audio is distorted.",
                value=300,
                emoji="⚠"
            )
        )
        options.append(
            discord.SelectOption(
                label="400%",
                description="Set volume to 400%. Most audio is distorted",
                value=400,
                emoji="⚠"
            )
        )
        options.append(
            discord.SelectOption(
                label="500%",
                description="Set volume to 500%. Everything is distorted",
                value=500,
                emoji="⚠"
            )
        )
        options.append(
            discord.SelectOption(
                label="1,000%",
                description="Set volume to 1,000%. Why?",
                value=1000,
                emoji=self.red_warning
            )
        )

        super().__init__(
            placeholder=f"🔊 Volume: {self.pp.player.volume}%",
            max_values=1,
            min_values=1,
            options=options,
            row=1,
            custom_id="volume",
            disabled=True,
        )
        
    async def callback(self, interaction: discord.Interaction):
        vol = int(self.values[0])
        await self.pp.player.set_volume(vol)
        self.placeholder = f"🔊 Volume: {self.pp.player.volume:,}%"
        await self.view.refresh_view()
        await interaction.response.edit_message()
        await self.pp.u.increment_statistic('MUSICBOT_VOLUME_CHANGED')