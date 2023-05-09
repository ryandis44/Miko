import discord
from tunables import *
from Database.GuildObjects import MikoMember


class ChecklistView(discord.ui.View):
    def __init__(self, original_interaction: discord.Interaction):
        super().__init__(timeout=tunables('YMCA_VIEW_TIMEOUT'))
        self.original_interaction = original_interaction
        self.u = MikoMember(user=original_interaction.user, client=original_interaction.client, check_exists=False)
    
    async def ainit(self):
        try: self.msg = await self.original_interaction.original_response()
        except: return
        await self.respond()
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.u.user.id
    
    async def on_timeout(self) -> None:
        try:
            msg = await self.original_interaction.original_response()
            await msg.delete()
        except: return
    
    
    # /checklist and back button response
    async def respond(self) -> None:
        temp = []
        temp.append(
            "Select a checklist below"
        )
        
        
        self.clear_items()
        
        embed = discord.Embed(description=''.join(temp), color=GREEN_BOOK_NEUTRAL_COLOR)
        embed.set_author(
            icon_url=self.u.guild.icon,
            name=f"{self.u.guild} Checklist"
        )
        return embed