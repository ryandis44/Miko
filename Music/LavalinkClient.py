import asyncio
import discord
from discord.ext import commands
import lavalink
from tunables import *

AUDIO_SESSIONS = {}

class LavalinkVoiceClient(discord.VoiceClient):
    """
    This is the preferred way to handle external voice sending
    This client will be created via a cls in the connect method of the channel
    see the following documentation:
    https://discordpy.readthedocs.io/en/latest/api.html#voiceprotocol
    """

    def __init__(self, client: discord.Client, channel: discord.abc.Connectable):
        self.client = client
        self.channel = channel
        # ensure a client already exists
        if hasattr(self.client, 'lavalink'):
            self.lavalink = self.client.lavalink
        else:
            self.client.lavalink = lavalink.Client(client.user.id)
            self.client.lavalink.add_node(
                'localhost',
                2333,
                'youshallnotpass',
                'us',
                'default-node'
            )
            self.lavalink = self.client.lavalink

    async def on_voice_server_update(self, data):
        # the data needs to be transformed before being handed down to
        # voice_update_handler
        lavalink_data = {
            't': 'VOICE_SERVER_UPDATE',
            'd': data
        }
        await self.lavalink.voice_update_handler(lavalink_data)

    async def on_voice_state_update(self, data):
        # the data needs to be transformed before being handed down to
        # voice_update_handler
        lavalink_data = {
            't': 'VOICE_STATE_UPDATE',
            'd': data
        }
        await self.lavalink.voice_update_handler(lavalink_data)

    async def connect(self, *, timeout: float, reconnect: bool, self_deaf: bool = False, self_mute: bool = False) -> None:
        """
        Connect the bot to the voice channel and create a player_manager
        if it doesn't exist yet.
        """
        # ensure there is a player_manager when creating a new voice_client
        self.lavalink.player_manager.create(guild_id=self.channel.guild.id)
        await self.channel.guild.change_voice_state(channel=self.channel, self_mute=self_mute, self_deaf=self_deaf)

    async def disconnect(self, *, force: bool = False) -> None:
        """
        Handles the disconnect.
        Cleans up running player and leaves the voice client.
        """
        player = self.lavalink.player_manager.get(self.channel.guild.id)

        # no need to disconnect if we are not connected
        if not force and not player.is_connected:
            return

        # None means disconnect
        await self.channel.guild.change_voice_state(channel=None)

        # update the channel_id of the player to None
        # this must be done because the on_voice_state_update that would set channel_id
        # to None doesn't get dispatched after the disconnect
        player.channel_id = None
        self.cleanup()

async def ensure_voice(interaction: discord.Interaction):
    """ This check ensures that the bot and command author are in the same voicechannel. """
    player = interaction.client.lavalink.player_manager.create(interaction.guild.id)
    # Create returns a player if one exists, otherwise creates.
    # This line is important because it ensures that a player always exists for a guild.

    # Most people might consider this a waste of resources for guilds that aren't playing, but this is
    # the easiest and simplest way of ensuring players are created.

    # These are commands that require the bot to join a voicechannel (i.e. initiating playback).
    # Commands such as volume/skip etc don't require the bot to be in a voicechannel so don't need listing here.
    should_connect = interaction.command.name in ('play',)

    if not interaction.user.voice or not interaction.user.voice.channel:
        # Our cog_command_error handler catches this and sends it to the voicechannel.
        # Exceptions allow us to "short-circuit" command invocation via checks so the
        # execution state of the command goes no further.
        raise commands.CommandInvokeError('Join a voicechannel first.')

    v_client = interaction.guild.voice_client
    if not v_client:
        if not should_connect:
            raise commands.CommandInvokeError('Not connected.')

        permissions = interaction.user.voice.channel.permissions_for(interaction.guild.me)

        if not permissions.connect or not permissions.speak:  # Check user limit too?
            raise commands.CommandInvokeError("I do not have `CONNECT` and/or `SPEAK` permissions for that channel.")

        player.store('channel', interaction.channel.id)
        await interaction.user.voice.channel.connect(cls=LavalinkVoiceClient)
        await interaction.guild.change_voice_state(
            channel=interaction.user.voice.channel,
            self_deaf=True,
            self_mute=False
        )
    else:
        if v_client.channel.id != interaction.user.voice.channel.id:
            raise commands.CommandInvokeError('You need to be in my voicechannel.')
