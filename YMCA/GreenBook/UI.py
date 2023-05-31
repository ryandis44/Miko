import discord
from misc.view_misc import LogChannel, ModalTryAgain, check_modal_error
from tunables import *
from YMCA.GreenBook.Objects import GreenBook, Person
from Database.GuildObjects import MikoMember
from Database.database_class import AsyncDatabase
db = AsyncDatabase("GreenBook.UI.py")


class BookView(discord.ui.View):
    def __init__(self, original_interaction: discord.Interaction):
        super().__init__(timeout=tunables('YMCA_VIEW_TIMEOUT'))
        self.original_interaction = original_interaction
        self.u = MikoMember(user=original_interaction.user, client=original_interaction.client, check_exists=False)
        self.book = GreenBook(self.u)
        
        self.res: list[Person] = None
        self.total_items = 0
        self.offset = 0

    async def ainit(self):
        await self.respond(init=True)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.u.user.id

    async def on_timeout(self) -> None:
        try:
            msg = await self.original_interaction.original_response()
            await msg.delete()
        except: return
    
    # /book and back button response
    async def respond(self, init=False) -> None:
        res = await self.book.recent_entries()
        total_entries = await self.book.total_entries
        self.total_items = len(res)
        async def __default_embed() -> discord.Embed:
            temp = []

            temp.append(
                "The YMCA Swim Test Book for keeping track of swim tests.\n"
                "This book can be accessed any time in this server "
                f"using {tunables('SLASH_COMMAND_SUGGEST_BOOK')}.\n"
                ""
                "Use the buttons below to search, add, or modify entries "
                "in the Swim Test Book.\n\n"
            )

            if self.total_items > 0: temp.append("__Recent entries__ `[Last Name, First Name]`:")
            else: temp.append("There are no entries in this book. Add one by pressing the  `New Entry`  button.")
            for result in res:
                temp.append(f"\n{result}")
            
            if self.total_items < total_entries:
                temp.append(f"... and {(total_entries - self.total_items):,} more\n\n")
            

            embed = discord.Embed(description=''.join(temp), color=GREEN_BOOK_NEUTRAL_COLOR)
            embed.set_author(
                icon_url=self.u.guild.icon,
                name=f"{self.u.guild} Swim Test Book"
            )
            return embed
        
        self.clear_items()
        self.add_item(SelectEntries(bview=self, res=res))
        self.add_item(NewEntry(bview=self))
        self.add_item(SearchButton(bview=self))
        if self.u.user.guild_permissions.manage_guild:
            self.add_item(LogChannelButton(bview=self))
        # if admin, add more stuff self.add_item(admin)
        # if total_entries > tunables('GREEN_BOOK_RECENT_ENTRIES_LIMIT'):
        #     self.__determine_button_status()
        #     f = FirstButton()
        #     p = PrevButton()
        #     n = NextButton()
        #     l = LastButton()
        #     f.disabled = p.disabled = self.button_status['p']
        #     l.disabled = n.disabled = self.button_status['n']
        #     self.add_item(f)
        #     self.add_item(p)
        #     self.add_item(n)
        #     self.add_item(l)

        if init: self.msg = await self.original_interaction.original_response()
        await self.msg.edit(
            content=None,
            embed=await __default_embed(),
            view=self
        )

    def __determine_button_status(self) -> None:
        self.button_status = {'p': True, 'n': True}
        if self.offset == 0: self.button_status = {'p': True, 'n': False}
        elif self.offset + tunables('GREEN_BOOK_RECENT_ENTRIES_LIMIT') >= self.total_items: self.button_status = {'p': False, 'n': True}
        elif self.offset > 0 and self.offset < self.total_items: self.button_status = {'p': False, 'n': False}
    
    def __check_offset(self) -> None:
        if self.offset < 0: self.offset = 0
        elif self.offset + tunables('GREEN_BOOK_RECENT_ENTRIES_LIMIT') >= self.total_items: self.offset = self.total_items - tunables('GREEN_BOOK_RECENT_ENTRIES_LIMIT')

    # Response after completing search modal
    async def respond_modal_search(self, modal=None, search=True) -> None:
        self.__check_offset()
        if modal is not None:
            self.res = await self.book.search(query=modal.name.value)
            self.total_items = len(self.res)
            self.offset = 0
            
        if self.total_items == 1:
            await self.respond_select_person(p=self.res[0])
            return

        def __search_embed() -> discord.Embed:
            temp = []

            if self.total_items == 0:
                temp.append(f"Could not find an entry matching `{modal.name.value}`")
                color = GREEN_BOOK_FAIL_COLOR
            else:
                if search: temp.append(f"__Search results__ ")
                temp.append("__`[Last Name, First Name]`__\n")
                color = GREEN_BOOK_NEUTRAL_COLOR
            cnt = 0
            for result in self.res[self.offset:self.offset+tunables('GREEN_BOOK_RECENT_ENTRIES_LIMIT')]:
                temp.append(f"`{cnt+1+self.offset}.` {result}\n")
                cnt += 1

            embed = discord.Embed(description=''.join(temp), color=color)
            embed.set_author(icon_url=self.u.guild.icon, name=f"{self.u.guild} Swim Test Book")
            embed.set_footer(
                text=(
                    f"Showing entries {self.offset+1 if cnt > 0 else 0} - {self.offset+cnt} "
                    f"of {self.total_items}"
                )
            )
            return embed
        
        self.clear_items()
        b = BackToMainButton(bview=self)
        b.row = 2
        self.add_item(b)
        self.add_item(SelectEntries(bview=self, res=self.res))
        self.add_item(SearchButton(bview=self))
        self.add_item(NewEntry(bview=self))
        if self.total_items > tunables('GREEN_BOOK_RECENT_ENTRIES_LIMIT'):
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

        await self.msg.edit(
            content=None,
            embed=__search_embed(),
            view=self
        )
        await self.u.increment_statistic('YMCA_GREEN_BOOK_ENTRIES_SEARCHED')

    # Response after choosing someone from the dropdown
    async def respond_select_person(self, p: Person) -> None:
        async def __selected_person_embed() -> discord.Embed:
            embed = discord.Embed(
                description=''.join(await self.__detailed_entry_embed_description(p=p)),
                color=GREEN_BOOK_NEUTRAL_COLOR
            )
            embed.set_author(
                icon_url=self.u.guild.icon,
                name=f"{self.u.guild} Swim Test Book"
            )
            return embed
        self.clear_items()
        self.add_item(BackToMainButton(bview=self))
        self.add_item(EditEntry(bview=self, p=p))
        if self.u.user.guild_permissions.manage_guild:
            self.add_item(DeleteEntry(bview=self, p=p))
        self.add_item(NewEntry(bview=self))
        self.add_item(SearchButton(bview=self))

        await self.msg.edit(
            content=None,
            embed=await __selected_person_embed(),
            view=self
        )

    # Description for full entry info
    async def __detailed_entry_embed_description(self, p: Person, history=True) -> list:
        temp = []
        
        if p.camp is not None: camp = f"Camp: :camping: **{p.camp}**\n"
        else: camp = ""

        temp.append(
            f"Full Entry Info for **{p.last}**, **{p.first}**:\n\n"

            f"{camp}"
            f"First Name: **{p.first}**\n"
            f"Last Name: **{p.last}**\n"
            f"Age: **{p.age}**\n"
            # f"DOB: "
            f"Wristband Level: {p.wristband_emoji} **{p.wristband}**\n"
            f"Entered: __{p.pass_time_formatted}__\n"
            f"By: {p.creator_id_mention}\n"
            # f"EID: `{p.eid}`\n"
        )

        hist = await p.history
        hist_len = len(hist)
        if hist_len == 0 and history:
            temp.append("\nThis entry has not been updated since its creation.")
        elif history:
            temp.append(
                f"\nThis entry has been updated `{hist_len if hist_len < 10 else 'more than 10'}` time{'s' if hist_len > 1 else ''}. "
                f"{'These are the latest updates:' if hist_len > 1 else 'This is the latest update:'}\n"
            )
            for update in hist:
                temp.append(f"\n{update}")
        
        return temp

    # Response for selecting individual user
    async def respond_detailed_entry(self, t: str, p: Person=None, modal=None) -> None:
        desc = []

        # Embed setup
        history=True
        match t:
            
            case 'EDIT':
                if await p.edit(modal=modal, modifier=self.u.user):
                    desc.append(
                        f":white_check_mark: __**Success! The entry for  `{p.last}, {p.first}`  has been updated.**__"
                    )
                    color = GREEN_BOOK_SUCCESS_COLOR
                    await self.u.increment_statistic('YMCA_GREEN_BOOK_ENTRIES_EDITED')
        
            case 'NEW':
                wristband = modal.wristband.value
                if wristband.upper() == "Y": wristband = "YELLOW"
                elif wristband.upper() == "R": wristband = "RED"
                else: wristband = "GREEN"
                p: Person = await self.book.create(
                    first=modal.first.value,
                    last=modal.last.value,
                    age=modal.age.value,
                    wristband=wristband,
                    camp=modal.camp.value
                )
                if p.new:
                    desc.append(
                        f":white_check_mark: __**Success!  `{p.last}, {p.first}`  has been added to the Swim Test Book.**__"
                    )
                    color = GREEN_BOOK_SUCCESS_COLOR
                else:
                    desc.append(
                        f":exclamation:  __**`{p.last}, {p.first}`  is already in the Swim Test Book. Here is their info:**__"
                    )
                    color = GREEN_BOOK_WARN_COLOR
                await self.u.increment_statistic('YMCA_GREEN_BOOK_ENTRIES_CREATED')

            case 'DELETE_WARN':
                desc.append(
                    f"⚠ __**Warning: You are about to remove  `{p.last}, {p.first}`  from the Swim Test Book. "
                    "Confirm deletion?**__"
                )
                history=False
                color = GREEN_BOOK_WARN_COLOR
            
            case 'DELETE_CONFIRM':
                desc.append(
                    f":white_check_mark: __**Success!  `{p.last}, {p.first}`  has been removed from the Swim Test Book.**__"
                )
                color = GREEN_BOOK_SUCCESS_COLOR
                await p.delete()
                await self.u.increment_statistic('YMCA_GREEN_BOOK_ENTRIES_DELETED')
            
            case 'DELETE_CANCEL':
                desc.append(
                    f":x: __**Cancelled.  `{p.last}, {p.first}`  was not removed from the Swim Test Book.**__"
                )
                color = GREEN_BOOK_FAIL_COLOR
                
            case _:
                color = GREEN_BOOK_NEUTRAL_COLOR



        if t not in ['DELETE_CONFIRM']:
            desc.append("\n\n")
            desc.append(''.join(await self.__detailed_entry_embed_description(p=p, history=history)))
        embed = discord.Embed(description=''.join(desc), color=color)
        embed.set_author(icon_url=self.u.guild.icon, name=f"{self.u.guild} Swim Test Book")

        self.clear_items()
        match t:
            case 'DELETE_WARN':
                self.add_item(DeleteCancel(bview=self, p=p))
                self.add_item(DeleteConfirm(bview=self, p=p))

            case 'DELETE_CONFIRM':
                self.add_item(BackToMainButton(bview=self))

            case _:
                self.add_item(BackToMainButton(bview=self))
                self.add_item(EditEntry(bview=self, p=p))
                if self.u.user.guild_permissions.manage_guild:
                    self.add_item(DeleteEntry(bview=self, p=p))
                self.add_item(NewEntry(bview=self))
                self.add_item(SearchButton(bview=self))

        await self.msg.edit(
            content=None,
            embed=embed,
            view=self
        )

class FirstButton(discord.ui.Button):

    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.gray,
            label=None,
            emoji=tunables('GENERIC_FIRST_BUTTON'),
            custom_id="first",
            row=4,
            disabled=True
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        self.view.offset = 0
        await self.view.respond_modal_search()

class PrevButton(discord.ui.Button):

    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.gray,
            label=None,
            emoji=tunables('GENERIC_PREV_BUTTON'),
            custom_id="prev",
            row=4,
            disabled=True
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        self.view.offset -= tunables('GREEN_BOOK_RECENT_ENTRIES_LIMIT')
        await self.view.respond_modal_search()

class NextButton(discord.ui.Button):

    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.gray,
            label=None,
            emoji=tunables('GENERIC_NEXT_BUTTON'),
            custom_id="next",
            row=4,
            disabled=True
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        self.view.offset += tunables('GREEN_BOOK_RECENT_ENTRIES_LIMIT')
        await self.view.respond_modal_search()

class LastButton(discord.ui.Button):

    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.gray,
            label=None,
            emoji=tunables('GENERIC_LAST_BUTTON'),
            custom_id="last",
            row=4,
            disabled=True
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        self.view.offset = self.view.total_items - tunables('GREEN_BOOK_RECENT_ENTRIES_LIMIT')
        await self.view.respond_modal_search()


class SearchButton(discord.ui.Button):

    def __init__(self, bview: BookView):
        super().__init__(
            style=discord.ButtonStyle.gray,
            label=None,
            emoji="🔎",
            custom_id="sea_button",
            row=2
        )
        self.bview = bview
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(self.SearchModal(bview=self.bview))

    class SearchModal(discord.ui.Modal):

        def __init__(self, bview: BookView):
            super().__init__(title="Search the book", custom_id="search_modal")
            self.bview = bview

        name = discord.ui.TextInput(
                label="Search by First/Last Name or Camp Name:",
                placeholder="Bradford",
                min_length=1,
                max_length=tunables('GREEN_BOOK_MAX_SEARCH_LENGTH')
            )
        async def on_submit(self, interaction: discord.Interaction) -> None:
            await interaction.response.edit_message()
            await self.bview.respond_modal_search(modal=self)


class BackToMainButton(discord.ui.Button):

    def __init__(self, bview: BookView):
        super().__init__(
            style=discord.ButtonStyle.blurple,
            label="Back",
            emoji=None,
            custom_id="back_button",
            row=1
        )
        self.bview = bview
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await self.bview.respond()


async def on_modal_submit(modal, interaction: discord.Interaction, p: Person=None) -> None:
    e = check_modal_error(modal=modal)
    if e['age'] or e['wristband']: raise Exception

    # Message gets deleted during error handling; except and pass
    try: await interaction.response.edit_message()
    except: pass
    if p is None: await modal.bview.respond_detailed_entry(t='NEW', modal=modal)
    else: await modal.bview.respond_detailed_entry(t='EDIT', modal=modal, p=p)

async def on_modal_error(modal, error_interaction: discord.Interaction):
        e = check_modal_error(modal=modal)
        
        temp = []
        if e['age']: temp.append("`Age` must be a number between 1 and 100.")
        if e['wristband']: temp.append("`Wristband Color` must be one letter: `r` for Red, `y` for Yellow, or `g` for Green (or leave empty for Green)")

        try:
            modal.first.default = modal.first.value
            modal.last.default = modal.last.value
        except: pass
        if not e['age']: modal.age.default = modal.age.value
        if not e['wristband']: modal.wristband.default = modal.wristband.value

        if not error_interaction.response.is_done():
            await error_interaction.response.send_message(
                content='\n'.join(temp),
                ephemeral=True,
                view=ModalTryAgain(calling_modal=modal, error_interaction=error_interaction)
            )


     
class FullEntryModal(discord.ui.Modal):

    def __init__(self, bview: BookView, p: Person=None):
        super().__init__(title="New Swim Test Book Entry", custom_id="entry_modal")
        self.bview = bview
        self.p = p

    first = discord.ui.TextInput(
            label="First Name:",
            placeholder="Chris",
            min_length=1,
            max_length=tunables('GREEN_BOOK_MAX_SEARCH_LENGTH'),
            default=None
        )
    
    last = discord.ui.TextInput(
            label="Last Name:",
            placeholder="Bradford",
            min_length=1,
            max_length=tunables('GREEN_BOOK_MAX_SEARCH_LENGTH'),
            default=None
        )
    
    age = discord.ui.TextInput(
            label="Age:",
            placeholder="12",
            min_length=1,
            max_length=3,
            default=None
        )

    wristband = discord.ui.TextInput(
            label="Wristband Color (Leave blank for green):",
            placeholder="r (red), y (yellow), g (green)",
            min_length=0,
            max_length=1,
            required=False,
            default=None
        )

    camp = discord.ui.TextInput(
            label="Camp Name (optional):",
            placeholder="Greenlake",
            min_length=0,
            max_length=tunables('GREEN_BOOK_MAX_SEARCH_LENGTH'),
            required=False,
            default=None
        )
    async def on_submit(self, interaction: discord.Interaction) -> None:
        await on_modal_submit(modal=self, interaction=interaction, p=self.p)
    
    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await on_modal_error(modal=self, error_interaction=interaction)


class AgeWristbandModal(discord.ui.Modal):

    def __init__(self, bview: BookView, p: Person):
        super().__init__(title="New Swim Test Book Entry", custom_id="entry_modal")
        self.bview = bview
        self.p = p
    
    age = discord.ui.TextInput(
            label="Age:",
            placeholder="12",
            min_length=1,
            max_length=3,
            default=None
        )

    wristband = discord.ui.TextInput(
            label="Wristband Color (Leave blank for green):",
            placeholder="r (red), y (yellow), g (green)",
            min_length=0,
            max_length=1,
            required=False,
            default=None
        )
    async def on_submit(self, interaction: discord.Interaction) -> None:
        await on_modal_submit(modal=self, interaction=interaction, p=self.p)
    
    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await on_modal_error(modal=self, error_interaction=interaction)


class NewEntry(discord.ui.Button):

    def __init__(self, bview: BookView):
        super().__init__(
            style=discord.ButtonStyle.green,
            label="New Entry",
            emoji=None,
            custom_id="new_button",
            row=2
        )
        self.bview = bview
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(FullEntryModal(bview=self.bview))


class EditEntry(discord.ui.Button):
    def __init__(self, bview: BookView, p: Person):
        super().__init__(
            style=discord.ButtonStyle.green,
            label=None,
            emoji="✏",
            custom_id="eit_entry_button",
            row=1
        )
        self.bview = bview
        self.p = p
        
        if self.bview.u.user.guild_permissions.manage_guild:
            self.m = FullEntryModal(bview=self.bview, p=self.p)
            self.m.first.default = p.first
            self.m.last.default = p.last
            self.m.camp.default = p.camp
        else:
            self.m = AgeWristbandModal(bview=self.bview, p=self.p)
        self.m.age.default = p.age
        self.m.wristband.default = p.wristband_letter
        

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(self.m)


class SelectEntries(discord.ui.Select):
    def __init__(self, bview: BookView, res: list):
        self.bview = bview
        self.res = res

        options = []
        disabled = True
        placeholder = "No entries found"
        for i, result in enumerate(res):
            result: Person = result
            options.append(
                discord.SelectOption(
                    label=f"{result.last}, {result.first}",
                    description=f"Age {result.age}",
                    value=i,
                    emoji=result.wristband_emoji
                )
            )

        if len(options) < 1:
            options.append(
                discord.SelectOption(
                    label="(no items)",
                    value="(no items)"
                )
            )
        else:
            disabled = False
            placeholder = "Select an entry from above"

        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options,
            row=1,
            custom_id="select_entry",
            disabled=disabled
        )
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message()
        p = self.res[int(self.values[0])]
        await self.bview.respond_select_person(p=p)

class DeleteEntry(discord.ui.Button):
    def __init__(self, bview: BookView, p: Person):
        super().__init__(
            style=discord.ButtonStyle.red,
            label="Delete",
            emoji=None,
            custom_id="delete_button",
            row=1
        )
        self.bview = bview
        self.p = p

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await self.bview.respond_detailed_entry(t='DELETE_WARN', p=self.p)

class DeleteCancel(discord.ui.Button):
    def __init__(self, bview: BookView, p: Person):
        super().__init__(
            style=discord.ButtonStyle.red,
            label=None,
            emoji="✖",
            custom_id="cancel_delete_button",
            row=1
        )
        self.bview = bview
        self.p = p

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await self.bview.respond_detailed_entry(t='DELETE_CANCEL', p=self.p)

class DeleteConfirm(discord.ui.Button):
    def __init__(self, bview: BookView, p: Person):
        super().__init__(
            style=discord.ButtonStyle.green,
            label=None,
            emoji="✔",
            custom_id="confirm_delete_button",
            row=1
        )
        self.bview = bview
        self.p = p

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await self.bview.respond_detailed_entry(t='DELETE_CONFIRM', p=self.p)


class LogChannelButton(discord.ui.Button):
    def __init__(self, bview: BookView):
        super().__init__(
            style=discord.ButtonStyle.blurple,
            label="Log Channel",
            emoji=None,
            custom_id="logc_button",
            row=2
        )
        self.bview = bview

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await LogChannel(
                original_interaction=interaction,
                typ="GREEN_BOOK",
                return_view=self.view
            ).ainit()