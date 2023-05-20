import discord
from YMCA.Checklist.Objects import Checklist, ChecklistItem
from tunables import *
from Database.GuildObjects import MikoMember


class ChecklistView(discord.ui.View):
    def __init__(self, original_interaction: discord.Interaction):
        super().__init__(timeout=tunables('YMCA_VIEW_TIMEOUT'))
        self.original_interaction = original_interaction
        self.u = MikoMember(user=original_interaction.user, client=original_interaction.client, check_exists=False)
        self.checklists: list[Checklist] = []
    
    async def ainit(self):
        try: self.msg = await self.original_interaction.original_response()
        except: return
        await self.get_checklists()
        await self.respond()
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.u.user.id
    
    async def on_timeout(self) -> None:
        try: await self.msg.delete()
        except: return
    
    async def get_checklists(self) -> None:
        for list in await self.u.checklists:
            if list.visible:
                self.checklists.append(list)
        
        self.__calculate_total_items()
        self.active_checklists = []
    
    def __calculate_total_items(self) -> None:
        self.total_items = 0
        for checklist in self.checklists:
            for item in checklist.items:
                self.total_items += 1
    
    @property
    def SelectItems(self):
        if self.active_checklists == []: return SelectList(items=self.checklists)
        
        l = SelectList(items=self.checklists)
        for i, option in enumerate(l.options):
            if i == 0:
                option.default = False
                continue
            if str(i) in self.active_checklists:
                option.default = True
        
        return l
    
    @property
    def listed_checklists(self) -> list[Checklist]:
        if self.active_checklists == []: return self.checklists
        
        temp = []
        for i, list in enumerate(self.checklists):
            if str(i+1) in self.active_checklists:
                temp.append(list)
        return temp
    
    # /checklist and home button response
    async def respond(self) -> None:
        temp = []
        temp.append(
            "__**Active checklists**__:\n\n"
        )
        
        
        items_on_page = []
        completed_items = []
        
        # Design 1
        for checklist in self.listed_checklists:
            temp.append(f"{checklist.emoji} **{checklist.name}**:")
            for item in checklist.items:
                if item.completed:
                    # completed_items.append(item)
                    # continue
                    temp.append(f"\n> :green_circle: __{item.name}__")
                    continue
                else:
                    temp.append(f"\n> :black_circle: __{item.name}__")
                
                if item.description is not None:
                    temp.append(f"\n> \u200b \u200b​└─{item.description}")
                
                items_on_page.append(item)
            
            temp.append("\n\n")
        
        
        
        
        
        embed = discord.Embed(description=''.join(temp), color=GREEN_BOOK_NEUTRAL_COLOR)
        embed.set_author(
            icon_url=self.u.guild.icon,
            name=f"{self.u.guild} Checklist"
        )
        embed.set_footer(text=f"Items on this page: {len(items_on_page)}")
        
        self.clear_items()
        self.add_item(self.SelectItems)
        # self.add_item(ItemList(items=items_on_page))
        
        await self.msg.edit(content=None, embed=embed, view=self)
    



class ItemList(discord.ui.Select):
    
    def __init__(self, items: list):
        self.items = items

        options = []
        for i, item in enumerate(items):
            item: ChecklistItem
            options.append(
                discord.SelectOption(
                    label=f"{item.name} {item.id}",
                    description=f"From list {item.checklist.name.upper()}",
                    value=i,
                    emoji=item.checklist.emoji
                )
            )

        super().__init__(
            placeholder="Check off an item",
            min_values=1,
            max_values=len(options),
            options=options,
            row=2,
            custom_id="select_item",
            disabled=False
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        pass

class SelectList(discord.ui.Select):

    def __init__(self, items: list):
        self.items = items

        options = []

        options.append(
            discord.SelectOption(
                label=f"All Checklists",
                description=None,
                value="0",
                emoji="*️⃣",
                default=True
            )
        )

        for i, item in enumerate(items):
            item: Checklist
            options.append(
                discord.SelectOption(
                    label=f"{item.name}",
                    description=f"ID {item.id}",
                    value=i+1,
                    emoji=item.emoji
                )
            )

        super().__init__(
            placeholder="Select a list",
            min_values=1,
            max_values=len(options),
            options=options,
            row=1,
            custom_id="select_entry",
            disabled=False
        )
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message()
        
        prev = self.view.active_checklists
        self.view.active_checklists = []
        for val in self.values:
            if val == "0":
                if prev == []: continue
                self.view.active_checklists = []
                break
            self.view.active_checklists.append(val)
        
        await self.view.respond()