import discord
from tunables import *
from Database.database_class import AsyncDatabase
from Database.GuildObjects import MikoMember
db = AsyncDatabase("ActivityCheck.Introductions.py")


class IntroductionsView(discord.ui.View):
    def __init__(self, original_interaction: discord.Interaction):
        super().__init__(timeout=tunables('GLOBAL_VIEW_TIMEOUT'))
        self.original_interaction = original_interaction
        self.u = MikoMember(user=self.original_interaction.user, client=self.original_interaction.client)

    async def ainit(self):
        await self.original_interaction.response.send_modal(IntroductionModal())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.u.user.id

    async def on_timeout(self) -> None:
        try:
            msg = await self.original_interaction.original_response()
            await msg.delete()
        except:
            try:
                await self.msg.delete()
            except: return
    
    async def respond(self) -> None:

        
                
        await self.msg.edit(
            content="WIP",
            embed=None,
            view=self
        )
    
    

class IntroductionModal(discord.ui.Modal):

    def __init__(self):
        super().__init__(title="Introduce Yourself", custom_id="introductions")

    name = discord.ui.TextInput(
            label="Name:",
            placeholder="Jefferson Andrade",
            min_length=1,
            max_length=tunables('GREEN_BOOK_MAX_SEARCH_LENGTH'),
            default=None
        )
    
    nickname = discord.ui.TextInput(
            label="Nickname (leave blank for none):",
            placeholder="Loli Lover/Head Giver",
            min_length=1,
            max_length=tunables('GREEN_BOOK_MAX_SEARCH_LENGTH'),
            default=None
        )
    
    pronouns = discord.ui.TextInput(
            label="Pronouns (leave blank for no preference):",
            placeholder="Bitch/Ass",
            min_length=1,
            max_length=3,
            default=None
        )

    major = discord.ui.TextInput(
            label="Major:",
            placeholder="Physics",
            min_length=0,
            max_length=1,
            required=False,
            default=None
        )

    other_info = discord.ui.TextInput(
            label="3 things about you and how did you find us?",
            # placeholder="",
            min_length=0,
            max_length=tunables('GREEN_BOOK_MAX_SEARCH_LENGTH'),
            required=False,
            default=None,
            style=discord.TextStyle.paragraph
        )
    async def on_submit(self, interaction: discord.Interaction) -> None:
        pass
    
    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        pass