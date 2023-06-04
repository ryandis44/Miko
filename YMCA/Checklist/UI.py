import discord
from YMCA.Checklist.Objects import Checklist, ChecklistItem, create_checklist
from misc.view_misc import LogChannel
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
        try: await self.respond()
        except Exception as e: print(e)
        self.num_visible_checklists = len(self.checklists)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.u.user.id
    
    async def on_timeout(self) -> None:
        try: await self.msg.delete()
        except: return
    
    async def get_checklists(self) -> None:
        self.checklists.clear()
        for list in await self.u.checklists():
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
    async def ItemListF(self):
        l = ItemList(items=self.items_on_page)
        roles = await self.u.ymca_checklist_allowed_roles
        check = any(role in self.u.user.roles for role in roles)
        if roles == [] or await self.u.manage_guild or check: return l
        
        l.disabled = True
        l.placeholder = "No permissions to check off items"
        
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
        log_channel = await self.u.ymca_checklist_channel
        for item in self.items_on_page: temp[item.id] = item
        
        # Complete all items in the 'items' list
        completed: list[str] = []
        for item in items:
            del temp[item.id]
            if await item.complete(u=self.u):
                completed.append(f"`{item.name}`")
        
        # Any item not in 'items' list, uncomplete
        for key, value in temp.items():
            value: ChecklistItem
            await value.uncomplete(u=self.u)
        
        if log_channel is not None and completed != []:
            await log_channel.send(
                content=(
                    f"{self.u.user.mention} completed " + ', '.join(completed)
                ), silent=True,
                allowed_mentions=discord.AllowedMentions(users=False)
            )
        
        # await self.get_checklists()
        await self.respond()
        
    async def item_edit_callback(self, modal, obj: Checklist|ChecklistItem) -> None:
        if type(obj) is Checklist:
            await obj.create_item(
                u=self.u,
                name=modal.name.value,
                desc=modal.desc.value
            )
        elif type(obj) is ChecklistItem:
            await obj.edit(
                name=modal.name.value,
                desc=modal.desc.value
            )
        
        
        await self.get_checklists()
        if type(obj) is Checklist: await self.respond_edit_checklist(checklist=obj)
        elif type(obj) is ChecklistItem: await self.respond_edit_item(item=obj)
        else: await self.respond_admin()
    
    # /checklist and home button response
    async def respond(self) -> None:
        
        lists = self.listed_checklists
        self.__calculate_total_items()
        self.__determine_pos()
        self.items_on_page: list[ChecklistItem] = []
        temp = []
        if len(lists) > 0:
            temp.append(
                "__**Active checklists**__:\n\n"
            )
            

            
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
            for checklist in lists:
                
                if checklist.resets != "DISABLED": resets_in = f" - Resets {checklist.resets_in_timestamp}"
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
        
        else:
            temp.append("There are no checklists associated with this guild.")
            
        embed = discord.Embed(description=''.join(temp), color=GREEN_BOOK_NEUTRAL_COLOR)
        embed.set_author(
            icon_url=self.u.guild.icon,
            name=f"{self.u.guild} Checklists"
        )
        
        if len(lists) > 0:
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
        if await self.u.manage_guild: self.add_item(AdminButton())
        try: self.add_item(await self.ItemListF)
        except Exception as e: print(e)
        
        await self.msg.edit(content=None, embed=embed, view=self)

    async def respond_admin(self) -> None:
        all_checklists = await self.u.checklists(include_hidden=True)
        num_checklists = len(all_checklists)
        
        temp = []
        
        temp.append(
            f"{num_checklists}/{tunables('MAX_CHECKLISTS_PER_GUILD')} checklists in this guild\n\n"
        )
        
        if num_checklists > 0:
            temp.append("__**All checklists**__:\n\n")
            
            temp.append("**Bold** checklists are visible to everyone\n")
            for checklist in all_checklists:
                temp.append(
                    f"{checklist.emoji} "
                    f"{checklist.bold_name_if_visible} - "
                    f"{len(checklist.items)} item(s)"
                )
                if checklist.resets != "DISABLED":
                    temp.append(
                        f" Resets `{checklist.resets}` "
                        f"{checklist.resets_in_timestamp}"
                    )
                    
                temp.append("\n")
        else:
            temp.append("Click `New Checklist` to get started")
        
        
        
        
        embed = discord.Embed(description=''.join(temp), color=GREEN_BOOK_NEUTRAL_COLOR)
        embed.set_author(
            icon_url=self.u.guild.icon,
            name=f"{self.u.guild} Checklists"
        )
        embed.set_footer(text=(
                f"{num_checklists} checklist{'s' if num_checklists != 1 else ''}, "
                f"{self.num_visible_checklists} visible checklist{'s' if self.num_visible_checklists != 1 else ''}"
            ))
        
        self.clear_items()
        self.add_item(EditChecklist(checklists=all_checklists))
        self.add_item(ReorderChecklists(checklists=all_checklists))
        self.add_item(ChooseChecklistToDelete(checklists=all_checklists))
        self.add_item(HomeButton())
        n = NewChecklist()
        n.disabled = num_checklists >= tunables('MAX_CHECKLISTS_PER_GUILD')
        self.add_item(n)
        self.add_item(LogChannelButton())
        try: self.add_item(PermissionsButton())
        except Exception as e: print(f"Permissions Button: {e}")
        await self.msg.edit(content=None, embed=embed, view=self)
        
    async def respond_permissions(self) -> None:
        roles = await self.u.ymca_checklist_allowed_roles
        
        temp = []
        temp.append(
            "Select roles below that will be able to check off "
            "items on the checklist. Selecting none allows everyone "
            "to check off items. **Max 20**"
            "\n\n"
        )
        
        if roles != []:
            temp.append("Selected roles:\n")
            prev = False
            for i, role in enumerate(roles):
                if prev: temp.append(", ")
                if i % 3 == 0 and i > 0: temp.append("\n")
                temp.append(f"{role.mention}")
                if not prev: prev = True
        else: temp.append("No roles selected. @everyone can check off items.")
        
        embed = discord.Embed(description=''.join(temp), color=GREEN_BOOK_NEUTRAL_COLOR)
        embed.set_author(
            icon_url=self.u.guild.icon,
            name=f"{self.u.guild} Checklists"
        )
        
        self.clear_items()
        self.add_item(SelectPermittedRoles())
        self.add_item(AdminButton(list="Poop"))
        rm = RemoveAllPermissionsButton()
        rm.disabled = roles == []
        self.add_item(rm)
        await self.msg.edit(content=None, embed=embed, view=self)

    async def respond_edit_checklist(self, checklist: Checklist) -> None:
        temp = []
        
        completed: list[ChecklistItem] = []
        incomplete: list[ChecklistItem] = []
        for item in checklist.items:
            if item.completed: completed.append(item)
            else: incomplete.append(item)
        
        temp.append(
            f"{checklist.emoji} {checklist.bold_name_if_visible} checklist selected"
            "\n\n"
            f"{len(completed)}/{len(checklist.items)} items completed\n"
            f"{len(checklist.items)}/{tunables('MAX_ITEMS_PER_CHECKLIST')} items in this checklist"
            "\n\n"
            f"Created by: {checklist.creator_mention}\n"
            f"Created: <t:{checklist.created_at}:F>\n"
            f"Resets: **{checklist.resets if checklist.resets != 'DISABLED' else 'Never'}** {checklist.resets_in_timestamp if checklist.resets_in_timestamp != '<t:None:R>' else ''}\n"
            "List visibility:"
            f"{checklist.list_visibility_status}"
            "\n\n"
            "All items (**bold** means complete):\n"
        )
        if checklist.items == []:
            temp.append("(No items)")
        for i, item in enumerate(checklist.items):
            temp.append(
                f"{i+1}. {item.bold_if_completed}\n"
            )
        
        
        embed = discord.Embed(description=''.join(temp), color=GREEN_BOOK_NEUTRAL_COLOR)
        embed.set_author(
            icon_url=self.u.guild.icon,
            name=f"{self.u.guild} Checklists"
        )
        
        self.clear_items()
        self.add_item(EditItem(items=checklist.items))
        self.add_item(ReorderItems(checklist=checklist))
        self.add_item(ChecklistResetSelector(checklist=checklist))
        self.add_item(AdminButton(list="Poop"))
        self.add_item(ChecklistHistory(checklist=checklist))
        self.add_item(ChecklistVisibility(checklist=checklist))
        n = NewItem(checklist=checklist)
        n.disabled = len(checklist.items) >= tunables('MAX_ITEMS_PER_CHECKLIST')
        self.add_item(n)
        self.add_item(EditChecklistButton(checklist=checklist))
        
        await self.msg.edit(content=None, embed=embed, view=self)

    async def respond_u_sure(self, obj: Checklist|ChecklistItem) -> None:
        temp = []
        temp.append(
            f"Are you sure?"
        )

        embed = discord.Embed(description=''.join(temp), color=GREEN_BOOK_NEUTRAL_COLOR, title=f"You are about to delete `{obj.name}`")
        embed.set_author(
            icon_url=self.u.guild.icon,
            name=f"{self.u.guild} Checklists",
        )
        
        self.clear_items()
        self.add_item(AdminButton(list=obj))
        self.add_item(DeleteItem(obj=obj))
        
        await self.msg.edit(content=None, embed=embed, view=self)

    async def respond_edit_item(self, item: ChecklistItem) -> None:
        temp = []
        temp.append(
            f"Name: **{item.name}**\n"
            f"Position: `{item.pos+1}`\n"
            f"Description:```{item.description}```"
            f"Created by: {item.creator_mention}\n"
            f"Created: {item.created_at_formatted}\n"
            f"Status:{item.completed_formatted}"
        )
        
        embed = discord.Embed(description=''.join(temp), color=GREEN_BOOK_NEUTRAL_COLOR)
        embed.set_author(
            icon_url=self.u.guild.icon,
            name=f"{self.u.guild} Checklists"
        )
        
        self.clear_items()
        self.add_item(AdminButton(list=item))
        self.add_item(DeleteItemFake(obj=item))
        self.add_item(ItemCompletionStatus(item=item))
        self.add_item(EditItemButton(item=item))
        
        await self.msg.edit(content=None, embed=embed, view=self)
    
    async def respond_checklist_history(self, checklist: Checklist) -> None:
        history = await checklist.history
        temp = []
        temp.append(f"Viewing last {tunables('MAX_VISIBLE_CHECKLIST_HISTORY')} updates to {checklist.emoji} {checklist.bold_name_if_visible}:\n\n")
        
        
        if history == []:
            temp.append("(No history)")
        for i, entry in enumerate(history):
            temp.append(
                f":black_medium_small_square: {i+1}. {entry.actor_mention} completed "
                f"**{entry.item_name}** on "
                f"{entry.completed_at_formatted}\n"
            )
        
        embed = discord.Embed(description=''.join(temp), color=GREEN_BOOK_NEUTRAL_COLOR)
        embed.set_author(
            icon_url=self.u.guild.icon,
            name=f"{self.u.guild} Checklists"
        )
        
        self.clear_items()
        self.add_item(AdminButton(list=checklist.items[0]))
        
        await self.msg.edit(content=None, embed=embed, view=self)


PAGE_BUTTONS_ROW = 4
SELECT_CHECKLISTS_ROW = 1
SELECT_ITEM_ROW = SELECT_CHECKLISTS_ROW + 1

class LogChannelButton(discord.ui.Button):

    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.blurple,
            label="Log Channel",
            custom_id="logccccc_button",
            row=PAGE_BUTTONS_ROW
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await LogChannel(
                original_interaction=interaction,
                typ="CHECKLIST",
                return_view=self.view
            ).ainit()

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

class PermissionsButton(discord.ui.Button):

    def __init__(self):
        
        s = discord.ButtonStyle
        super().__init__(
            style=s.gray,
            label="Permissions",
            emoji=tunables('GENERIC_PERMISSIONS_BUTTON'),
            custom_id="permissions_button",
            row=PAGE_BUTTONS_ROW
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await self.view.respond_permissions()

class RemoveAllPermissionsButton(discord.ui.Button):

    def __init__(self):
        
        s = discord.ButtonStyle
        super().__init__(
            style=s.red,
            label="Remove all",
            custom_id="remove_all_perms",
            row=PAGE_BUTTONS_ROW
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await db.execute(f"DELETE FROM CHECKLIST_PERMISSIONS WHERE server_id='{interaction.guild.id}'")
        await self.view.respond_permissions()

class SelectPermittedRoles(discord.ui.RoleSelect):
    def __init__(self):

        super().__init__(
            placeholder="Select role(s)",
            min_values=1,
            max_values=20,
            row=SELECT_CHECKLISTS_ROW,
            custom_id="select_roles",
            disabled=False
        )
    
    async def callback(self, interaction: discord.Interaction):
        roles = self.values
        await interaction.response.edit_message()
        await db.execute(
            "DELETE FROM CHECKLIST_PERMISSIONS WHERE "
            f"server_id='{interaction.guild.id}'"
        )
        temp = [
            "INSERT INTO CHECKLIST_PERMISSIONS (server_id,role_id) VALUES "
        ]
        prev = False
        for role in roles:
            if prev: temp.append(", ")
            temp.append(
                f"('{interaction.guild.id}', '{role.id}')"
            )
            if not prev: prev = True
        
        await db.execute(''.join(temp))
        await self.view.respond_permissions()

class AdminButton(discord.ui.Button):

    def __init__(self, list: Checklist|ChecklistItem = None):
        self.list = list
        
        s = discord.ButtonStyle
        super().__init__(
            style=s.red if list is None else s.gray,
            label=None if list is None else "Back",
            emoji=tunables('GENERIC_SETTINGS_BUTTON') if list is None else None,
            custom_id="admin_button",
            row=PAGE_BUTTONS_ROW
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        
        if type(self.list) is ChecklistItem: await self.view.respond_edit_checklist(self.list.checklist)
        else: await self.view.respond_admin()
        
        # case doesnt work here for some reason
        # match type(self.list):
        #     case Checklist(): await self.view.respond_edit_checklist(self.list)
        #     case ChecklistItem():
        #         print("Item type found")
        #         await self.view.respond_edit_checklist(self.list.checklist)
        #     case None: print("None found")
        #     case _: await self.view.respond_admin()

class HomeButton(discord.ui.Button):

    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.gray,
            label=None,
            emoji=tunables('GENERIC_HOME_BUTTON'),
            custom_id="home_button",
            row=PAGE_BUTTONS_ROW
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await self.view.respond()

class ChecklistHistory(discord.ui.Button):

    def __init__(self, checklist: Checklist):
        self.checklist = checklist
        super().__init__(
            style=discord.ButtonStyle.gray,
            label=None,
            emoji=tunables('GENERIC_HISTORY_BUTTON'),
            custom_id="history_button",
            row=PAGE_BUTTONS_ROW,
            disabled=True if checklist.items == [] else False
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await self.view.respond_checklist_history(self.checklist)

class ItemCompletionStatus(discord.ui.Button):

    def __init__(self, item: ChecklistItem):
        s = discord.ButtonStyle
        self.item = item
        completed = item.completed
        super().__init__(
            style=s.green if completed else s.red,
            label="Complete" if completed else "Incomplete",
            emoji="✔" if completed else "✖",
            custom_id="toggle_button_completion",
            row=PAGE_BUTTONS_ROW
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await self.item.toggle_completion(u=MikoMember(user=interaction.user, client=interaction.client))
        await self.item.checklist.ainit()
        await self.view.get_checklists()
        await self.view.respond_edit_item(self.item)
        
class ChecklistVisibility(discord.ui.Button):

    def __init__(self, checklist: Checklist):
        s = discord.ButtonStyle
        self.checklist = checklist
        super().__init__(
            style=s.green if checklist.raw_visibility else s.red,
            label="Visible" if checklist.raw_visibility else "Not Visible",
            emoji="✔" if checklist.raw_visibility else "✖",
            custom_id="toggle_button",
            row=PAGE_BUTTONS_ROW
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await self.checklist.toggle_visibility()
        await self.view.get_checklists()
        await self.view.respond_edit_checklist(self.checklist)

class DeleteItemFake(discord.ui.Button):

    def __init__(self, obj: Checklist|ChecklistItem):
        self.obj = obj
        super().__init__(
            style=discord.ButtonStyle.red,
            label="Delete",
            emoji=None,
            custom_id="delete_item",
            row=PAGE_BUTTONS_ROW,
            disabled=False
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await self.view.respond_u_sure(self.obj)

class DeleteItem(discord.ui.Button):

    def __init__(self, obj: Checklist|ChecklistItem):
        self.obj = obj
        super().__init__(
            style=discord.ButtonStyle.red,
            label="Delete",
            emoji=None,
            custom_id="delete_item",
            row=PAGE_BUTTONS_ROW,
            disabled=False
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await self.obj.delete()
        await self.view.get_checklists()
        if type(self.obj) is Checklist:
            await self.view.respond_admin()
        elif type(self.obj) is ChecklistItem:
            await self.obj.checklist.ainit()
            await self.view.respond_edit_checklist(self.obj.checklist)
        
class NewItem(discord.ui.Button):

    def __init__(self, checklist: Checklist):
        self.checklist = checklist
        super().__init__(
            style=discord.ButtonStyle.green,
            label="New Item",
            emoji=None,
            custom_id="new_item",
            row=PAGE_BUTTONS_ROW,
            disabled=True
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(ItemModal(title="New Item", bview=self.view, obj=self.checklist))
        
class NewChecklist(discord.ui.Button):

    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.green,
            label="New Checklist",
            custom_id="fdasfdfdd",
            row=PAGE_BUTTONS_ROW,
            disabled=False
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        m = ChecklistModal(title="New Checklist", bview=self.view)
        await interaction.response.send_modal(m)
        
class EditChecklistButton(discord.ui.Button):

    def __init__(self, checklist: Checklist):
        self.checklist = checklist
        super().__init__(
            style=discord.ButtonStyle.green,
            label=None,
            emoji=tunables('GENERIC_EDIT_BUTTON'),
            custom_id="edit_checklist_b",
            row=PAGE_BUTTONS_ROW,
            disabled=False
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        m = ChecklistModal(title="Edit Checklist", bview=self.view, checklist=self.checklist)
        m.name.default = self.checklist.name
        await interaction.response.send_modal(m)
        
class EditItemButton(discord.ui.Button):

    def __init__(self, item: ChecklistItem):
        self.item = item
        super().__init__(
            style=discord.ButtonStyle.green,
            label=None,
            emoji=tunables('GENERIC_EDIT_BUTTON'),
            custom_id="edit_item_b",
            row=PAGE_BUTTONS_ROW,
            disabled=False
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        m = ItemModal(title="Edit Item", obj=self.item, bview=self.view)
        m.name.default = self.item.name
        m.desc.default = self.item.description
        await interaction.response.send_modal(m)

class ChecklistModal(discord.ui.Modal):

    def __init__(self, title: str, bview: ChecklistView, checklist: Checklist = None):
        self.bview = bview
        self.checklist = checklist
        super().__init__(title=title, custom_id="item_modal")

    name = discord.ui.TextInput(
            label="Checklist Name",
            placeholder="Daily",
            min_length=1,
            max_length=tunables('MAX_CHECKLIST_NAME_LENGTH'),
            default=None,
            required=True
        )
    # desc = discord.ui.TextInput(
    #         label="Checklist Description",
    #         placeholder="before i kiss yours",
    #         min_length=0,
    #         max_length=tunables('MAX_CHECKLIST_DESCRIPTION_LENGTH'),
    #         default=None,
    #         required=False
    #     )
    
    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        if self.checklist is None: await create_checklist(interaction=interaction, name=self.name.value)
        else: await self.checklist.edit(name=self.name.value)
        await self.bview.get_checklists()
        if self.checklist is None: await self.bview.respond_admin()
        else: await self.bview.respond_edit_checklist(self.checklist)

class ItemModal(discord.ui.Modal):

    def __init__(self, title: str, bview: ChecklistView, obj: Checklist|ChecklistItem):
        self.bview = bview
        self.obj = obj
        super().__init__(title=title, custom_id="item_modal")

    name = discord.ui.TextInput(
            label="Item Name",
            placeholder="Kiss my ass",
            min_length=1,
            max_length=tunables('MAX_CHECKLIST_ITEM_NAME_LENGTH'),
            default=None,
            required=True
        )
    desc = discord.ui.TextInput(
            label="Item Description",
            placeholder="before i kiss yours",
            min_length=0,
            max_length=tunables('MAX_CHECKLIST_ITEM_DESCRIPTION_LENGTH'),
            default=None,
            required=False
        )
    
    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await self.bview.item_edit_callback(modal=self, obj=self.obj)
    
    # async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
    #     await on_modal_error(modal=self, error_interaction=interaction)

class EditChecklist(discord.ui.Select):

    def __init__(self, checklists: list):
        self.checklists = checklists

        options = []
        disabled = True
        placeholder = "No checklists found"
        for i, checklist in enumerate(checklists):
            checklist: Checklist
            options.append(
                discord.SelectOption(
                    label=f"{checklist.name}",
                    description=None if checklist.resets == "DISABLED" else \
                        f"Resets {checklist.resets}",
                    value=i,
                    emoji=checklist.emoji
                )
            )

        if options == []:
            options.append(
                discord.SelectOption(
                    label="(no items)",
                    value="(no items)"
                )
            )
        else:
            disabled = False
            placeholder = "Select a checklist to edit"

        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options,
            row=SELECT_CHECKLISTS_ROW,
            custom_id="edit_checklist",
            disabled=disabled
        )
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message()
        try: await self.view.respond_edit_checklist(self.checklists[int(self.values[0])])
        except Exception as e: print(e)

class EditItem(discord.ui.Select):
    
    def __init__(self, items: list):
        self.items = items

        options = []
        disabled = True
        placeholder = "No items found"
        for i, item in enumerate(items):
            item: ChecklistItem
            options.append(
                discord.SelectOption(
                    label=item.name,
                    description=item.description,
                    value=i,
                    emoji="◽"
                )
            )
        
        if options == []:
            options.append(
                discord.SelectOption(
                    label="(no items)",
                    value="(no items)"
                )
            )
        else:
            disabled = False
            placeholder = "Edit an item"

        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options,
            row=SELECT_CHECKLISTS_ROW,
            custom_id="edit_item",
            disabled=disabled
        )


    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await self.view.respond_edit_item(self.items[int(self.values[0])])

class ChecklistResetSelector(discord.ui.Select):
    
    def __init__(self, checklist: Checklist):
        self.checklist = checklist

        options = [
            discord.SelectOption(
                label="Reset Disabled",
                value="DISABLED",
                emoji="❌",
                default=True if checklist.resets == "DISABLED" else False
            ),
            discord.SelectOption(
                label="Daily Reset",
                value="DAILY",
                emoji="⏰",
                default=True if checklist.resets == "DAILY" else False
            ),
            discord.SelectOption(
                label="Weekly Reset",
                value="WEEKLY",
                emoji="📆",
                default=True if checklist.resets == "WEEKLY" else False
            ),
            discord.SelectOption(
                label="Monthly Reset",
                value="MONTHLY",
                emoji="🗓",
                default=True if checklist.resets == "MONTHLY" else False
            )
        ]

        if options == []:
            options.append(
                discord.SelectOption(
                    label="(no items)",
                    value="(no items)"
                )
            )

        super().__init__(
            placeholder="Select reset status",
            min_values=1,
            max_values=1,
            options=options,
            row=SELECT_ITEM_ROW+1,
            custom_id="reset_setting",
            disabled=False
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await self.checklist.set_resets(resets=self.values[0])
        await self.view.get_checklists()
        await self.view.respond_edit_checklist(self.checklist)

class ReorderChecklists(discord.ui.Select):
    
    def __init__(self, checklists: list[Checklist]):
        self.checklists = checklists

        options = []
        disabled = True
        placeholder = "Not enough checklists to reorder"
        for i, checklist in enumerate(checklists):
            options.append(
                discord.SelectOption(
                    label=checklist.name,
                    value=checklist.id,
                    emoji=checklist.emoji
                )
            )

        if len(options) <= 1:
            options.append(
                discord.SelectOption(
                    label="(no items)",
                    value="(no items)"
                )
            )
        else:
            disabled = False
            placeholder = "Change checklist order"

        super().__init__(
            placeholder=placeholder,
            min_values=len(options),
            max_values=len(options),
            options=options,
            row=SELECT_ITEM_ROW,
            custom_id="reorder_checklists",
            disabled=disabled
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        for i, id in enumerate(self.values):
            await db.execute(
                f"UPDATE CHECKLISTS SET pos='{i}' WHERE "
                f"checklist_id='{id}'"
            )
        await self.view.get_checklists()
        await self.view.respond_admin()
        
class ChooseChecklistToDelete(discord.ui.Select):
    
    def __init__(self, checklists: list[Checklist]):
        self.checklists = checklists

        options = []
        disabled = True
        placeholder = "No checklists found"
        for i, checklist in enumerate(checklists):
            options.append(
                discord.SelectOption(
                    label=checklist.name,
                    value=i,
                    emoji=checklist.emoji
                )
            )

        if options == []:
            options.append(
                discord.SelectOption(
                    label="(no items)",
                    value="(no items)"
                )
            )
        else:
            disabled = False
            placeholder = "Delete a checklist"

        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options,
            row=SELECT_ITEM_ROW+1,
            custom_id="delete_checklists",
            disabled=disabled
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await self.view.respond_u_sure(self.checklists[int(self.values[0])])

class ReorderItems(discord.ui.Select):
    
    def __init__(self, checklist: Checklist):
        self.checklist = checklist

        options = []
        disabled = True
        placeholder = "Not enough items to reorder"
        for i, item in enumerate(checklist.items):
            item: ChecklistItem
            options.append(
                discord.SelectOption(
                    label=item.name,
                    value=item.id,
                    emoji="◽"
                )
            )

        if len(options) <= 1:
            options.append(
                discord.SelectOption(
                    label="(no items)",
                    value="(no items)"
                )
            )
        else:
            disabled = False
            placeholder = "Change item order"

        super().__init__(
            placeholder=placeholder,
            min_values=len(options),
            max_values=len(options),
            options=options,
            row=SELECT_ITEM_ROW,
            custom_id="reorder_items",
            disabled=disabled
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await self.checklist.reorder_items(order=self.values)
        await self.view.get_checklists()
        await self.view.respond_edit_checklist(self.checklist)

class ItemList(discord.ui.Select):
    
    def __init__(self, items: list):
        self.items = items

        options = []
        disabled = True
        placeholder = "No items found"
        for i, item in enumerate(items):
            item: ChecklistItem
            options.append(
                discord.SelectOption(
                    label=f"{item.name}",
                    description=(
                            f"{item.checklist.name} - "
                            f"{'Incomplete' if not item.completed else 'Complete'}"
                        ),
                    value=i,
                    emoji=item.checklist.emoji,
                    default=item.completed
                )
            )


        if options == []:
            options.append(
                discord.SelectOption(
                    label="(no items)",
                    value="(no items)"
                )
            )
        else:
            disabled = False
            placeholder = "Check off an item"

        super().__init__(
            placeholder=placeholder,
            min_values=0,
            max_values=len(options),
            options=options,
            row=SELECT_ITEM_ROW,
            custom_id="select_item",
            disabled=disabled
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
        disabled = True
        placeholder = "No checklists found"
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

        if len(options) <= 1:
            options.append(
                discord.SelectOption(
                    label="(no items)",
                    value="(no items)"
                )
            )
        else:
            disabled = False
            placeholder = "Select a checklist"


        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=len(options),
            options=options,
            row=SELECT_CHECKLISTS_ROW,
            custom_id="select_entry",
            disabled=disabled
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