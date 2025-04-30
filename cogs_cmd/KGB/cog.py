'''

KGB - Pterodactyl API Integration specific to KGB server management

'''



import discord
import os

from cogs_cmd.AnimeSearch.AnimeSearch import AnimeSearchView
from Database.MikoCore import MikoCore
from discord import app_commands
from discord.ext import commands
from cogs_cmd.Pterodactyl.Backend import PterodactylActions



GUILD_IDS = [890638458211680256]



class KGBCog(commands.Cog):
    def __init__(self, client):
        self.client: discord.Client = client



    start = app_commands.Group(name="startkgb", description="Start KGB Containers", guild_ids=GUILD_IDS)
    stop = app_commands.Group(name="stopkgb", description="Stop KGB Containers", guild_ids=GUILD_IDS)



    @start.command(name="all", description=f"Start all KGB containers")
    @app_commands.guild_only
    async def kgb_startall(self, interaction: discord.Interaction):

        mc = MikoCore()
        ptero = PterodactylActions(mc=mc, interaction=interaction)
        await ptero.signal_server(signal='start', server_ids=mc.tunables('KGB_SERVER_IDS').splitlines())



    @stop.command(name="all", description=f"Stop all KGB containers")
    @app_commands.guild_only
    async def kgb_stopall(self, interaction: discord.Interaction):

        mc = MikoCore()
        ptero = PterodactylActions(mc=mc, interaction=interaction)
        await ptero.signal_server(signal='stop', server_ids=mc.tunables('KGB_SERVER_IDS').splitlines())



    @start.command(name="container", description=f"Start a KGB container by name")
    @app_commands.guild_only
    async def kgb_start(self, interaction: discord.Interaction, name: str):

        mc = MikoCore()
        ptero = PterodactylActions(mc=mc, interaction=interaction)
        try: server_id = await ptero.get_server_by_name(name=name, context='KGB')
        except ValueError as e:
            msg = await interaction.original_response()
            await msg.edit(
                content=f"{mc.tunables('ERROR_EMOJI')} {e}"
            )
            return
        await ptero.signal_server(signal='start', server_ids=[server_id])



    @stop.command(name="container", description=f"Stop a KGB container by name")
    @app_commands.guild_only
    async def kgb_stop(self, interaction: discord.Interaction, name: str):

        mc = MikoCore()
        ptero = PterodactylActions(mc=mc, interaction=interaction)
        try: server_id = await ptero.get_server_by_name(name=name, context='KGB')
        except ValueError as e:
            msg = await interaction.original_response()
            await msg.edit(
                content=f"{mc.tunables('ERROR_EMOJI')} {e}"
            )
            return
        await ptero.signal_server(signal='stop', server_ids=[server_id])
        


    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        mc = MikoCore()
        await mc.user_ainit(user=interaction.user, client=self.client)
        if mc.profile.cmd_enabled('KGB') == 0:
            await interaction.response.send_message(content=mc.tunables('COMMAND_DISABLED_GUILD_MESSAGE'), ephemeral=True)
            return False
        elif mc.profile.cmd_enabled('KGB') == 2:
            await interaction.response.send_message(content=mc.tunables('COMMAND_DISABLED_MESSAGE'), ephemeral=True)
            return False
        
        if str(interaction.user.id) not in mc.tunables('KGB_ADMIN_IDS').splitlines():
            await interaction.response.send_message(content=mc.tunables('KGB_NOT_AUTHORIZED'), ephemeral=False, silent=True)
            return False

        await interaction.response.send_message(content=f"{mc.tunables('LOADING_EMOJI')}", ephemeral=False, silent=True)
        return True


async def setup(client: commands.Bot):
    await client.add_cog(KGBCog(client))