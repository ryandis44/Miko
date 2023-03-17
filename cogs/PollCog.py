import discord
from discord.ext import commands
from discord import app_commands
from Database.GuildObjects import MikoMember
from Polls.UI import PollCreateModal
from tunables import *
import os
from dotenv import load_dotenv
load_dotenv()


class PollCog(commands.Cog):
    def __init__(self, client):
        self.client: discord.Client = client

    group = app_commands.Group(name="poll", description="Poll Commands")
    @commands.Cog.listener()
    async def on_ready(self):
        self.tree = app_commands.CommandTree(self.client)


    @group.command(name="create", description=f"{os.getenv('APP_CMD_PREFIX')}Create a poll")
    @app_commands.guild_only
    async def poll_create(self, interaction: discord.Interaction):

        await interaction.response.send_modal(PollCreateModal())

    # @group.command(name="list", description=f"{os.getenv('APP_CMD_PREFIX')}Lists active polls in this server")
    # @app_commands.guild_only
    # async def poll_end(self, interaction: discord.Interaction):
    #     u = MikoMember(user=interaction.user, client=interaction.client)
    #     poll = active_polls.get_val(key=f"{interaction.user.id}{interaction.guild.id}")
    #     if poll is None:
    #         await interaction.response.send_message(content=tunables('POLL_NOT_FOUND'), ephemeral=True)
    #         return
    #     await interaction.response.send_message(embed=ongoing_results(author=interaction.user), ephemeral=True)
        


    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        u = MikoMember(user=interaction.user, client=interaction.client)
        await u.ainit()
        if not (await u.profile).cmd_enabled('POLL'):
            await interaction.response.send_message(content=tunables('GENERIC_BOT_DISABLED_MESSAGE'), ephemeral=True)
            return False
        
        if not tunables('POLLS_ENABLED'):
            await interaction.response.send_message(content=tunables('POLLS_DISABLED_MESSAGE'), ephemeral=True)
            return False

        return True


async def setup(client: commands.Bot):
    await client.add_cog(PollCog(client))