'''

Pterodactyl API Integration

'''



import discord
import os

from cogs_cmd.AnimeSearch.AnimeSearch import AnimeSearchView
from Database.MikoCore import MikoCore
from discord import app_commands
from discord.ext import commands
from cogs_cmd.Pterodactyl.Backend import PterodactylActions



class PterodactylCog(commands.Cog):
    def __init__(self, client):
        self.client: discord.Client = client



    group = app_commands.Group(name="ptero", description="Miscellaneous Pterodactyl commands", guild_ids=[890638458211680256])



    @group.command(name="kgb", description=f"{os.getenv('APP_CMD_PREFIX')}Run a pterodactyl command")
    @app_commands.guild_only
    @app_commands.choices(
        do=[
            app_commands.Choice(name="Start All", value='startall'),
            app_commands.Choice(name="Stop All", value='stopall'),
        ]
    )
    async def kgb(self, interaction: discord.Interaction, do: app_commands.Choice[str]):

        mc = MikoCore()
        await mc.user_ainit(user=interaction.user, client=self.client)

        ptero = PterodactylActions(mc=mc, interaction=interaction)
        
        match do.value:
            
            case 'startall': await ptero.signal_all(signal='start')
            case 'stopall': await ptero.signal_all(signal='stop')
        


    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        mc = MikoCore()
        await mc.user_ainit(user=interaction.user, client=self.client)
        if mc.profile.cmd_enabled('PTERODACTYL') == 0:
            await interaction.response.send_message(content=mc.tunables('COMMAND_DISABLED_GUILD_MESSAGE'), ephemeral=True)
            return False
        elif mc.profile.cmd_enabled('PTERODACTYL') == 2:
            await interaction.response.send_message(content=mc.tunables('COMMAND_DISABLED_MESSAGE'), ephemeral=True)
            return False
        
        if str(interaction.user.id) not in mc.tunables('PTERODACTYL_ADMIN_IDS').splitlines():
            await interaction.response.send_message(content=mc.tunables('PTERODACTYL_NOT_AUTHORIZED'), ephemeral=False, silent=True)
            return False

        await interaction.response.send_message(content=f"{mc.tunables('LOADING_EMOJI')}", ephemeral=False, silent=True)
        return True


async def setup(client: commands.Bot):
    await client.add_cog(PterodactylCog(client))