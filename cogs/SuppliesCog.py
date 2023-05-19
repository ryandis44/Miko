import os
import discord
from tunables import *
from discord.ext import commands
from discord import app_commands
from Database.GuildObjects import MikoMember
from YMCA.Supplies.UI import SuppliesView
from dotenv import load_dotenv
load_dotenv()
        

class SuppliesCog(commands.Cog):
    def __init__(self, client):
        self.client: discord.Client = client
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.tree = app_commands.CommandTree(self.client)


    @app_commands.command(name="supplies", description=f"{os.getenv('APP_CMD_PREFIX')}Notify management of supply needs [YMCA Servers Only]")
    @app_commands.guild_only
    async def supplies(self, interaction: discord.Interaction):
        await SuppliesView(original_interaction=interaction).ainit()


    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        u = MikoMember(user=interaction.user, client=interaction.client)
        await u.ainit()
        if (await u.profile).cmd_enabled('SUPPLIES') == 0:
            await interaction.response.send_message(content=tunables('COMMAND_DISABLED_GUILD'), ephemeral=True)
            return False
        elif (await u.profile).cmd_enabled('SUPPLIES') == 2:
            await interaction.response.send_message(content=tunables('COMMAND_DISABLED_TUNABLES'), ephemeral=True)
            return False

        await u.increment_statistic('YMCA_SUPPLIES_COMMAND_RUN')
        return True



async def setup(client: commands.Bot):
    await client.add_cog(SuppliesCog(client))