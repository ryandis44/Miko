import discord
from tunables import *
from Database.GuildObjects import MikoMember, AsyncDatabase
db = AsyncDatabase("Checklist.UI.py")


class ChecklistView(discord.ui.View):
    def __init__(self, original_interaction: discord.Interaction):
        super().__init__(timeout=tunables('GLOBAL_VIEW_TIMEOUT'))
        self.original_interaction = original_interaction
        self.u = MikoMember(user=original_interaction.user, client=original_interaction.client)

    async def ainit(self):
        self.message = await self.original_interaction.original_response()
        await self.respond(init=True)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.u.user.id

    async def on_timeout(self) -> None:
        try: await self.message.delete()
        except: return
    
    # /book and back button response
    async def respond(self, init=False) -> None:
        temp = []
        temp.append(
            "Everything possible with discord embeds:\n\n"
            
            "*Italics* **Bold** ~~Strikethrough~~ __Underline__ "
            "***__combination__***"
        )
        
        
        embed = discord.Embed(color=GLOBAL_EMBED_COLOR, description=''.join(temp))
        embed.set_author(icon_url=self.u.guild.icon, name=f"{self.u.guild.name} Checklist")
        try:
            self.clear_items()
            self.add_item(ExampleButton1())
            self.add_item(ExampleButton2())
            self.add_item(ExampleButton3())
            self.add_item(ExampleButton4())
            self.add_item(ExampleButton5())
        except Exception as e: print(e)

        await self.message.edit(content=None, embed=embed, view=self)
        

class SelectItem(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Up to 25 options here",
                description="100 characters max",
                value=1,
                emoji="🤡"
            )
        ]

        super().__init__(
            placeholder="Put some text here",
            min_values=1,
            max_values=1,
            options=options,
            row=1,
            custom_id="select_entry",
            disabled=False
        )
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message()

class ExampleButton1(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.red,
            label=None,
            emoji="✖",
            custom_id="cancel_delete_butt",
            row=2
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()

class ExampleButton2(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.green,
            label="hi",
            emoji=None,
            custom_id="cancel_delete_button",
            row=2
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()

class ExampleButton3(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.blurple,
            label=None,
            emoji="▶",
            custom_id="canceelete_button",
            row=2
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()

class ExampleButton4(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.url,
            label="Website",
            emoji=None,
            row=2,
            url="https://google.com/"
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()

class ExampleButton5(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.gray,
            label="idk",
            emoji="📌",
            custom_id="te_button",
            row=2
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()