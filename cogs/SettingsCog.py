import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from Database.GuildObjects import MikoMember
from Settings.Views import SettingsScopeView, SettingsView
from Settings.embeds import settings_initial
from tunables import *
from Database.database_class import Database
import os
from dotenv import load_dotenv
load_dotenv()

sc = Database("SettingsCog.py")


class SettingsCog(commands.Cog):
    def __init__(self, client):
        self.client: discord.Client = client

    @commands.Cog.listener()
    async def on_ready(self):
        self.tree = app_commands.CommandTree(self.client)


    @app_commands.command(name="settings", description=f"{os.getenv('APP_CMD_PREFIX')}Modify Miko settings for yourself or this guild (if you have permission)")
    @app_commands.guild_only
    async def settings(self, interaction: discord.Interaction):

        await SettingsView(original_interaction=interaction).ainit()

        # msg = await interaction.original_response()
        # await msg.edit(
        #     content=None,
        #     embed=settings_initial(interaction),
        #     view=SettingsScopeView(original_interaction=interaction)
        # )

    @app_commands.command(name="msettings", description=f"{os.getenv('APP_CMD_PREFIX')}Modify Miko settings for yourself or this guild (if you have permission)")
    @app_commands.guild_only
    async def msettings(self, interaction: discord.Interaction):

        msg = await interaction.original_response()
        await msg.edit(
            content=None,
            embed=settings_initial(interaction),
            view=SettingsScopeView(original_interaction=interaction)
        )



    async def interaction_check(self, interaction: discord.Interaction):
        await interaction.response.send_message(content=tunables('LOADING_EMOJI'), ephemeral=True)
        return True

async def setup(client: commands.Bot):
    await client.add_cog(SettingsCog(client))