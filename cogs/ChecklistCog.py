import os
import discord
from tunables import *
from discord.ext import commands
from discord import app_commands
from YMCA.Checklist.UI import ChecklistView
from Database.GuildObjects import MikoMember
        

class ChecklistCog(commands.Cog):
    def __init__(self, client):
        self.client: discord.Client = client
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.tree = app_commands.CommandTree(self.client)


    @app_commands.command(name="checklist", description=f"{os.getenv('APP_CMD_PREFIX')}Open the Checklist [YMCA Servers Only]")
    @app_commands.guild_only
    async def book(self, interaction: discord.Interaction):
        try: await ChecklistView(original_interaction=interaction).ainit()
        except Exception as e: print(e)


    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        u = MikoMember(user=interaction.user, client=interaction.client)
        await u.ainit()
        check = (await u.profile).cmd_enabled('CHECKLIST')
        if check == 0:
            await interaction.response.send_message(content=tunables('COMMAND_DISABLED_TUNABLES'), ephemeral=True)
            return False
        elif check == 2:
            await interaction.response.send_message(content=tunables('COMMAND_DISABLED_GUILD'))
            return False

        await interaction.response.send_message(content=f"{tunables('LOADING_EMOJI')}", ephemeral=True)
        await u.increment_statistic('CHECKLIST_OPENED')
        return True



async def setup(client: commands.Bot):
    await client.add_cog(ChecklistCog(client))