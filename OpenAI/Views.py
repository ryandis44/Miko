import discord
from tunables import *


# Main settings class responsible for entire settings menu interaction
class MikoGPTView(discord.ui.View):
    def __init__(self, messages: list) -> None:
        super().__init__(timeout=tunables('GLOBAL_VIEW_TIMEOUT'))
        self.add_item()

    async def on_timeout(self) -> None:
        self.clear_items()
        try: await self.msg.edit(view=self)
        except: pass
    

class RegenerateButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(
            style=discord.ButtonStyle.gray,
            label=None,
            emoji=tunables('GENERIC_REDO_BUTTON'),
            custom_id="prev_button",
            row=2,
            disabled=False
        )
    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.settings_list_page(interaction)