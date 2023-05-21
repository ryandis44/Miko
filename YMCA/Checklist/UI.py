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
        self.offset: int = 0
    
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
        # self.offset = 0
        self.checklists.clear()
        for list in await self.u.checklists:
            if list.visible:
                self.checklists.append(list)
        
        self.active_checklists = []
    
    def __calculate_total_items(self) -> None:
        self.total_items = 0
        for checklist in self.listed_checklists:
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
    
    def __determine_button_status(self) -> None:
        self.button_status = {'p': True, 'n': True}
        if self.offset == 0: self.button_status = {'p': True, 'n': False}
        elif self.offset + tunables('MAX_CHECKLIST_ITEMS_PER_PAGE') >= self.total_items: self.button_status = {'p': False, 'n': True}
        elif self.offset > 0 and self.offset < self.total_items: self.button_status = {'p': False, 'n': False}
    
    def __determine_pos(self) -> None:
        if self.offset < 0: self.offset = 0 # offset cannot be negative
        self.pos = 0
        if self.offset + tunables('MAX_CHECKLIST_ITEMS_PER_PAGE') <= self.total_items: self.pos = self.offset
        elif self.offset > 0: self.pos = self.offset = self.total_items - tunables('MAX_CHECKLIST_ITEMS_PER_PAGE')
    
    
    async def item_update_callback(self, items: list[ChecklistItem]) -> None:
        temp = {}
        for item in self.items_on_page: temp[item.id] = item
        
        # Complete all items in the 'items' list
        for item in items:
            del temp[item.id]
            await item.complete(u=self.u)
        
        # Any item not in 'items' list, uncomplete
        for key, value in temp.items():
            value: ChecklistItem
            await value.uncomplete(u=self.u)
        
        # await self.get_checklists()
        await self.respond()
        
    
    # /checklist and home button response
    async def respond(self) -> None:
        temp = []
        temp.append(
            "__**Active checklists**__:\n\n"
        )
        
        self.__calculate_total_items()
        self.__determine_pos()
        
        '''
        In these loops, 'i' is the total number of successful iterations
        and 'j' is the total number of iterations.
        
        'i' is used to determine when do stop appending items to the current
        page and 'j' is used to determine when to start appending items
        to the current page.
        '''
        # Design 1
        i = 0
        j = 0
        self.items_on_page: list[ChecklistItem] = []
        for checklist in self.listed_checklists:
            
            if checklist.resets != "DISABLED": resets_in = f" - Resets <t:{checklist.resets_in}:R>"
            else: resets_in = ""
            temp.append(f"{checklist.emoji} **{checklist.name}**{resets_in}")
            for item in checklist.items:
                if j < self.pos:
                    j+=1
                    continue
                if i >= tunables('MAX_CHECKLIST_ITEMS_PER_PAGE'): break
                
                self.items_on_page.append(item)
                if item.completed:
                    temp.append(f"\n> :green_circle: __{item.name}__")
                    i+=1
                    continue
                else:
                    temp.append(f"\n> :black_circle: __{item.name}__")
                
                if item.description is not None:
                    temp.append(f"\n> \u200b \u200b​└─{item.description}")
                
                i+=1
            
            temp.append("\n\n")
        
        # print(i, j, self.pos, self.offset)
        
        
        
        
        
        embed = discord.Embed(description=''.join(temp), color=GREEN_BOOK_NEUTRAL_COLOR)
        embed.set_author(
            icon_url=self.u.guild.icon,
            name=f"{self.u.guild} Checklist"
        )
        embed.set_footer(
            text=(
                f"Showing items {self.pos+1} - {self.pos+len(self.items_on_page)} of "
                f"{self.total_items}"
            )
        )
        
        self.clear_items()
        self.add_item(self.SelectItems)
        if self.total_items > tunables('MAX_CHECKLIST_ITEMS_PER_PAGE'):
            self.__determine_button_status()
            f = FirstButton()
            p = PrevButton()
            n = NextButton()
            l = LastButton()
            f.disabled = p.disabled = self.button_status['p']
            l.disabled = n.disabled = self.button_status['n']
            self.add_item(f)
            self.add_item(p)
            self.add_item(n)
            self.add_item(l)
            
            
        '''
        Add permissions allowing ONLY supervisors to modify
        completion status of an item
        '''
        self.add_item(ItemList(items=self.items_on_page))
        
        await self.msg.edit(content=None, embed=embed, view=self)


PAGE_BUTTONS_ROW = 1
SELECT_CHECKLISTS_ROW = 2
SELECT_ITEM_ROW = 3

class FirstButton(discord.ui.Button):

    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.gray,
            label=None,
            emoji=tunables('GENERIC_FIRST_BUTTON'),
            custom_id="first_button",
            row=PAGE_BUTTONS_ROW
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        self.view.offset = 0
        await self.view.respond()
        
class PrevButton(discord.ui.Button):

    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.gray,
            label=None,
            emoji=tunables('GENERIC_PREV_BUTTON'),
            custom_id="prev_button",
            row=PAGE_BUTTONS_ROW
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        self.view.offset -= tunables('MAX_CHECKLIST_ITEMS_PER_PAGE')
        await self.view.respond()
        
class NextButton(discord.ui.Button):

    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.gray,
            label=None,
            emoji=tunables('GENERIC_NEXT_BUTTON'),
            custom_id="next_button",
            row=PAGE_BUTTONS_ROW
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        self.view.offset += tunables('MAX_CHECKLIST_ITEMS_PER_PAGE')
        await self.view.respond()
        
class LastButton(discord.ui.Button):

    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.gray,
            label=None,
            emoji=tunables('GENERIC_LAST_BUTTON'),
            custom_id="last_button",
            row=PAGE_BUTTONS_ROW
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        self.view.offset = self.view.total_items - tunables('MAX_CHECKLIST_ITEMS_PER_PAGE')
        await self.view.respond()

class ItemList(discord.ui.Select):
    
    def __init__(self, items: list):
        self.items = items

        options = []
        for i, item in enumerate(items):
            item: ChecklistItem
            options.append(
                discord.SelectOption(
                    label=f"{item.name}",
                    # description=(
                    #         f"{item.checklist.name} - "
                    #         f"{'Incomplete' if not item.completed else 'Complete'}"
                    #     ),
                    description=f"{item.id}",
                    value=i,
                    emoji=item.checklist.emoji,
                    default=item.completed
                )
            )

        super().__init__(
            placeholder="Check off an item",
            min_values=0,
            max_values=len(options),
            options=options,
            row=SELECT_ITEM_ROW,
            custom_id="select_item",
            disabled=False
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        temp = []
        for val in self.values: temp.append(self.view.items_on_page[int(val)])
        await self.view.item_update_callback(temp)

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
                    # description=f"ID {item.id}",
                    value=i+1,
                    emoji=item.emoji
                )
            )

        super().__init__(
            placeholder="Select a list",
            min_values=1,
            max_values=len(options),
            options=options,
            row=SELECT_CHECKLISTS_ROW,
            custom_id="select_entry",
            disabled=False
        )
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message()
        
        self.view.offset = 0
        prev = self.view.active_checklists
        self.view.active_checklists = []
        for val in self.values:
            if val == "0":
                if prev == []: continue
                self.view.active_checklists = []
                break
            self.view.active_checklists.append(val)
        
        await self.view.respond()