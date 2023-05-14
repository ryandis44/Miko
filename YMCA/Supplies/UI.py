import discord
from misc.view_misc import LogChannel
from tunables import *
from YMCA.GreenBook.Objects import GreenBook, Person
from Database.GuildObjects import MikoMember
from Database.database_class import AsyncDatabase
db = AsyncDatabase("YMCA.Supplies.UI.py")


class SuppliesView(discord.ui.View):
    def __init__(self, original_interaction: discord.Interaction):
        super().__init__(timeout=tunables('YMCA_VIEW_TIMEOUT'))
        self.original_interaction = original_interaction
        self.u = MikoMember(user=original_interaction.user, client=original_interaction.client)
        self.msg = None

    async def ainit(self):
        await self.respond()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.u.user.id

    async def on_timeout(self) -> None:
        try:
            msg = await self.original_interaction.original_response()
            await msg.delete()
        except: return
    
    # GUI only if admin
    async def respond(self) -> None:
        self.supply_channel = await self.u.ymca_supplies_channel
        if await self.u.manage_guild:
            desc = (
                f"Current notification channel: {self.supply_channel.mention if self.supply_channel is not None else '`None`'}"
                "\n\n"
                "Select the channel to receive supply messages "
                "or create a new supply requirement."
            )
            
            embed = discord.Embed(color=GLOBAL_EMBED_COLOR, description=desc)
            embed.set_author(
                icon_url=self.u.guild.icon,
                name=f"{self.u.guild.name} Supply Needs"
            )
            
            self.clear_items()
            n = NewRequestButton()
            if self.supply_channel is None: n.disabled=True
            self.add_item(n)
            self.add_item(LogChannelButton())
            if self.msg is None:
                await self.original_interaction.response.send_message(
                    content=None,
                    embed=embed,
                    view=self,
                    ephemeral=True
                )
                self.msg = await self.original_interaction.original_response()
            else:
                await self.msg.edit(
                    content=None,
                    embed=embed,
                    view=self
                )
            return
        
        if self.supply_channel is None:
            await self.original_interaction.response.send_message(
                content="Error: Please let an admin know they have not designated a channel to receive supply channel messages.",
                ephemeral=True
            )
            return
        await self.original_interaction.response.send_modal(NewRequestModal(supply_channel=self.supply_channel))


class NewRequestModal(discord.ui.Modal):
    def __init__(self, supply_channel: discord.TextChannel, u: MikoMember):
        self.u = u
        super().__init__(
            title="What do we need to get/replace for the pool?",
            custom_id="supplyyy_modal"
        )
        self.supply_channel = supply_channel

    supply = discord.ui.TextInput(
            label="What do we need? (One per line)",
            placeholder="Ex: Guard Packs\nWhistles\nBands\netc.",
            min_length=1,
            max_length=tunables('YMCA_SUPPLIES_MAX_INPUT_LENGTH'),
            style=discord.TextStyle.paragraph,
            required=True
        )
    async def on_submit(self, interaction: discord.Interaction) -> None:
        try: await interaction.response.edit_message()
        except: pass
        
        items = []
        s = self.supply.value.split("\n")
        for item in s: items.append(f"- {item}\n")
        
        await self.supply_channel.send(
            content=(
                f"New supply request from {interaction.user.mention} (`{await self.u.username}`):\n"
                "```yaml\n"
                f"{''.join(items)}"
                "```"
            ), allowed_mentions=discord.AllowedMentions(users=False)
        )
        


class NewRequestButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.green,
            label="New",
            emoji=None,
            custom_id="newwwww_button",
            row=1
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(NewRequestModal(supply_channel=self.view.supply_channel, u=self.view.u))

class LogChannelButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.blurple,
            label="Log Channel",
            emoji=None,
            custom_id="logccccc_button",
            row=1
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await LogChannel(
                original_interaction=interaction,
                typ="SUPPLIES",
                return_view=self.view
            ).ainit()