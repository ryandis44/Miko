import discord
from discord.ext import commands
from discord import app_commands
from ActivityCheck.Introductions import IntroductionsView
from Database.GuildObjects import MikoMember
from tunables import *
from Database.database_class import Database
import re
import os
from dotenv import load_dotenv
load_dotenv()

hc = Database("HelpCog.py")
        

class IntroductionsCog(commands.Cog):
    def __init__(self, client):
        self.client: discord.Client = client
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.tree = app_commands.CommandTree(self.client)


    @app_commands.command(name="introductions", description=f"{os.getenv('APP_CMD_PREFIX')}Introductions setting page")
    @app_commands.guild_only
    async def introductions(self, interaction: discord.Interaction):
        try:
            await IntroductionsView(original_interaction=interaction).ainit()
        except Exception as e: print(e)




    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        u = MikoMember(user=interaction.user, client=interaction.client)
        await u.ainit()
        

        if (await u.profile).cmd_enabled('INTRODUCTIONS') == 0:
            await interaction.response.send_message(content=tunables('COMMAND_DISABLED_GUILD'), ephemeral=True)
            return False
        elif (await u.profile).cmd_enabled('INTRODUCTIONS') == 2:
            await interaction.response.send_message(content=tunables('COMMAND_DISABLED_TUNABLES'), ephemeral=True)
            return False
        
        # await interaction.response.send_message(content=f"{tunables('LOADING_EMOJI')}", ephemeral=True)
        await u.increment_statistic('INTRODUCTIONS_COMMAND')
        return True



async def setup(client: commands.Bot):
    await client.add_cog(IntroductionsCog(client))