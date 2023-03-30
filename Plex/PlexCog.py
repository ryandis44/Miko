import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from Database.GuildObjects import MikoMember
from Plex.embeds import plex_upcoming, plex_multi_embed
from tunables import *
from Database.database_class import Database
import aiohttp
import os
from dotenv import load_dotenv
load_dotenv()
sdb = Database("app_commands.py")


class PlexCog(commands.Cog):
    def __init__(self, client):
        self.client: discord.Client = client

    group = app_commands.Group(name="plex", description="Plex related commands", guild_ids=[890638458211680256])
    @commands.Cog.listener()
    async def on_ready(self):
        self.tree = app_commands.CommandTree(self.client)


    @group.command(name="calendar", description=f"{os.getenv('APP_CMD_PREFIX')}Displays upcoming Plex Calendar")
    @app_commands.guild_only
    async def set_level_roles(self, interaction: discord.Interaction):

        u = MikoMember(user=interaction.user, client=interaction.client)
        msg = await interaction.original_response()
        embeds = plex_multi_embed()


        for i, embed in enumerate(embeds):
            try: await interaction.user.send(embed=embed)
            except discord.Forbidden as e:
                await msg.edit(
                    content=(
                        "I cannot send you a DM because your privacy settings block me from messaging you."
                        "\n**Please turn on Direct Messages**:"
                        "\n```1. Right-click server icon"
                        "\n2. Go to Privacy Settings\n3. Turn on Direct Messages```"
                        "You can turn this back off after I message you if you wish."
                    )
                )
                break
            await asyncio.sleep(1)
            if i+1 == len(embeds): await msg.edit(content="Please check your DMs for the updated calendar.")




    async def interaction_check(self, interaction: discord.Interaction):
        u = MikoMember(user=interaction.user, client=interaction.client)
        await u.ainit()
        if (await u.profile).cmd_enabled('PLEX_CALENDAR') != 1:
            await interaction.response.send_message("This command can only be run in **The Boys Hangout** guild.\nhttps://discord.gg/the-boys", ephemeral=True)
            return False

        if await u.bot_permission_level >= 0:
            await interaction.response.send_message(f"{tunables('LOADING_EMOJI')}", ephemeral=True)
            return True
        
        await interaction.response.send_message(tunables('NO_PERM'), ephemeral=True)
        return False



async def setup(client: commands.Bot):
    await client.add_cog(PlexCog(client))