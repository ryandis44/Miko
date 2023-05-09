import discord
from YMCA.Checklist.Objects import Checklist
from misc.misc import emojis_1to10
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
        try: await self.msg.delete()
        except: return
    
    
    # /checklist and back button response
    async def respond(self) -> None:
        temp = []
        temp.append(
            "Select a checklist below"
        )
        
        embed = discord.Embed(description=''.join(temp), color=GREEN_BOOK_NEUTRAL_COLOR)
        embed.set_author(
            icon_url=self.u.guild.icon,
            name=f"{self.u.guild} Checklist"
        )
        
        self.clear_items()
        self.add_item(SelectList(items=await self.u.checklists))
        
        
        await self.msg.edit(
            content=None,
            embed=embed,
            view=self
        )
    
    async def respond_list_selected(self, list: Checklist) -> None:
        temp = []
        
        temp.append("Items in this checklist:\n\n")
        
        
        
        
        i = 0
        completed = []
        for item in list.items:
            
            if item.completed():
                completed.append(f"~~{item.name}~~\n")
                continue
            
            temp.append(f"{emojis_1to10(i)} **{item.name}**")
            if item.description is not None:
                temp.append(f":\n\u200b \u200b​└─ {item.description}")
            
            temp.append("\n")
            i+=1
        
        if completed != []:
            temp.append("\n")
            temp.append(''.join(completed))
        
        
        
        embed = discord.Embed(description=''.join(temp), color=GREEN_BOOK_NEUTRAL_COLOR)
        embed.set_author(
            icon_url=self.u.guild.icon,
            name=f"{list.name} Checklist"
        )
        
        
        self.clear_items()
        
        
        await self.msg.edit(
            content=None,
            embed=embed,
            view=self
        )



class SelectList(discord.ui.Select):

    def __init__(self, items: list):
        self.items = items

        options = []

        for i, item in enumerate(items):
            item: Checklist
            options.append(
                discord.SelectOption(
                    label=f"{item.name}",
                    description=f"ID {item.id}",
                    value=i,
                    emoji=emojis_1to10(i)
                )
            )

        super().__init__(
            placeholder="Select a list",
            min_values=1,
            max_values=1,
            options=options,
            row=1,
            custom_id="select_entry",
            disabled=False
        )
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message()
        l = self.items[int(self.values[0])]
        await self.view.respond_list_selected(l)