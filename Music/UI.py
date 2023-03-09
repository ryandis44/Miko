import asyncio
import time
import discord
from discord.ext import commands
from misc.misc import emojis_1to10, sanitize_track_name, time_elapsed
from tunables import *
from Music.LavalinkClient import AUDIO_SESSIONS
from Music.PersistentPlayer import PersistentPlayer
from Database.GuildObjects import MikoMember

        


class PlaylistButtons(discord.ui.View):
    def __init__(self, original_interaction: discord.Interaction, results):
        super().__init__(timeout=tunables('MUSIC_VIEW_TIMEOUT'))
        self.original_interaction = original_interaction
        self.u = MikoMember(
            user=original_interaction.user,
            client=original_interaction.client,
            check_exists=False
        )
        self.results = results

    async def on_timeout(self) -> None:
        msg = await self.original_interaction.original_response()
        await msg.delete()
    
    @discord.ui.button(style=discord.ButtonStyle.red, label="✖", custom_id="cancel_playlist")
    async def cancel_playlist(self, interaction: discord.Interaction, button = discord.Button):
        msg = await self.original_interaction.original_response()
        await msg.edit(embed=None, view=None, content="Playlist load cancelled.")
        await asyncio.sleep(tunables('QUICK_EPHEMERAL_DELETE_AFTER'))
        try: await msg.delete()
        except: pass
        await self.stop()

    @discord.ui.button(style=discord.ButtonStyle.green, label="✔", custom_id="load_playlist")
    async def load_playlist(self, interaction: discord.Interaction, button = discord.Button):
        msg = await self.original_interaction.original_response()

        if self.u.music_channel is None:
            ad = f"\n\n{tunables('MUSIC_BOT_MUSIC_CHANNEL_AD')}"
        else: ad = ""
        await msg.edit(content=f"Added {len(self.results.tracks)} songs to queue.{ad}", embed=None, view=None)

        try: sesh = AUDIO_SESSIONS[self.original_interaction.guild.id]
        except:
            AUDIO_SESSIONS[self.original_interaction.guild.id] = PersistentPlayer(
                original_interaction=self.original_interaction
            )
            sesh = AUDIO_SESSIONS[self.original_interaction.guild.id]

        await sesh.play(
            tracks=self.results.tracks,
            requester=self.original_interaction.user.id
        )

        mc = self.u.music_channel
        if mc is None: return
        await mc.send(
            content=f"🎶 {self.u.user.mention} added `{len(self.results.tracks)} songs` to the queue.",
            allowed_mentions=discord.AllowedMentions(users=False)
        )

        await asyncio.sleep(tunables('QUICK_EPHEMERAL_DELETE_AFTER'))
        try: await msg.delete()
        except: pass
        await self.stop()


'''
The following two classes, SongSelectView and SongSelectDropdown
are responsible for showing the user a list of songs from their
search query and prompting them to select one from the list to
add to the player queue.
'''
class SongSelectView(discord.ui.View):
    def __init__(self, original_interaction: discord.Interaction, results):
        super().__init__(timeout=tunables('MUSIC_VIEW_TIMEOUT'))
        self.original_interaction = original_interaction
        self.add_item(
            SongSelectDropdown(
                original_interaction=original_interaction,
                results=results
            )
        )
    
    async def on_timeout(self) -> None:
        msg = await self.original_interaction.original_response()
        await msg.delete()

class SongSelectDropdown(discord.ui.Select):
    def __init__(self, original_interaction: discord.Interaction, results):
        self.original_interaction = original_interaction
        self.results = results
        self.u = MikoMember(
            user=original_interaction.user,
            client=original_interaction.client,
            check_exists=False
        )

        options = []
        i = 0
        for track in results.tracks:
            i += 1
            options.append(
                discord.SelectOption(
                    label=sanitize_track_name(track),
                    description=track['author'],
                    value=i,
                    emoji=emojis_1to10(i-1)
                )
            )
            if i >= 10: break

        super().__init__(
            placeholder="Select an option",
            max_values=1,
            min_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        # await ensure_voice(interaction=self.original_interaction)
        track = self.results.tracks[int(self.values[0]) - 1]
        
        if self.u.music_channel is None:
            ad = f"\n\n{tunables('MUSIC_BOT_MUSIC_CHANNEL_AD')}"
        else: ad = ""

        msg = await self.original_interaction.original_response()
        await msg.edit(
            content=f"Added `{track['title']}` by `{track['author']}` to queue.{ad}",
            embed=None,
            view=None
        )

        u = MikoMember(user=self.original_interaction.user, client=self.original_interaction.client, check_exists=False)
        try: sesh = AUDIO_SESSIONS[self.original_interaction.guild.id]
        except:
            AUDIO_SESSIONS[self.original_interaction.guild.id] = PersistentPlayer(
                    original_interaction=self.original_interaction
                )
            sesh = AUDIO_SESSIONS[self.original_interaction.guild.id]
        
        mc = u.music_channel
        if mc is not None:
            await mc.send(
                content=f"🎵 {u.user.mention} added `{track.title}` by `{track.author}` to the queue.",
                allowed_mentions=discord.AllowedMentions(
                    users=False
                )
            )
        await sesh.play(
            tracks=track,
            requester=self.original_interaction.user.id
        )
















def song_search_results(results):
    temp = []

    temp.append(f"This embed will expire in <t:{int(time.time() + tunables('MUSIC_VIEW_TIMEOUT'))}:R>\n\n")

    temp.append("`[`, `]`, `*`, `_` _removed from titles for formatting purposes_\n")

    tracks = results.tracks
    i = 0
    for track in tracks:
        i += 1
        dur = time_elapsed(int(track.duration / 1000), ":")
        track.title = sanitize_track_name(track)
        temp.append(f"{emojis_1to10(i-1)} <:youtube:1031277947463675984> **{track['author']}**: [{track.title}]({track['uri']}) • `{dur}`\n")

        if i >= 10: break


    embed = discord.Embed (
        title = f'Search Results',
        color = GLOBAL_EMBED_COLOR,
        description=f"{''.join(temp)}"
    )

    return embed

def show_playlist_result(results):
    temp = []
    
    temp.append(f"This embed will expire in <t:{int(time.time() + tunables('MUSIC_VIEW_TIMEOUT'))}:R>\n\n")
    
    temp.append("<a:right_arrow_animated:1011515382672150548> Load YouTube playlist from link?\n\n")
    temp.append("`[`, `]`, `*`, `_` _removed from titles for formatting purposes_\n")
    i = 0
    cnt = len(results.tracks)
    for track in results.tracks:
        i += 1
        dur = time_elapsed(int(track.duration / 1000), ":")
        track.title = sanitize_track_name(track)
        temp.append(f"{emojis_1to10(i-1)} <:youtube:1031277947463675984> **{track['author']}**: [{track.title}]({track['uri']}) • `{dur}`\n")
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