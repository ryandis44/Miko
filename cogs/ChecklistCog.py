import os
import discord
from Checklist.UI import ChecklistView
from tunables import *
from discord.ext import commands
from discord import app_commands
from Database.GuildObjects import MikoMember
from dotenv import load_dotenv
load_dotenv()
        

class ChecklistCog(commands.Cog):
    def __init__(self, client):
        self.client: discord.Client = client
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.tree = app_commands.CommandTree(self.client)


    @app_commands.command(name="checklist", description=f"{os.getenv('APP_CMD_PREFIX')}View/Edit Checklist")
    @app_commands.guild_only
    async def book(self, interaction: discord.Interaction):
        await ChecklistView(original_interaction=interaction).ainit()


    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        u = MikoMember(user=interaction.user, client=interaction.client)
        await u.ainit()
        if (await u.profile).cmd_enabled('CHECKLIST') != 1:
            await interaction.response.send_message(content=tunables('GENERIC_BOT_DISABLED_MESSAGE'), ephemeral=True)
            return False

        await interaction.response.send_message(content=f"{tunables('LOADING_EMOJI')}", ephemeral=False)
        await u.increment_statistic('CHECKLIST_OPENED')
        return True



async def setup(client: commands.Bot):
    await client.add_cog(ChecklistCog(client))