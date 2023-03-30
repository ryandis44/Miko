import discord
from tunables import *
from GreenBook.Objects import GreenBook, Person
from Database.GuildObjects import MikoMember
from Database.database_class import AsyncDatabase
db = AsyncDatabase("GreenBook.UI.py")


class ChecklistView(discord.ui.View):
    def __init__(self, original_interaction: discord.Interaction):
        super().__init__(timeout=tunables('BOOK_VIEW_TIMEOUT'))
        self.original_interaction = original_interaction
        self.u = MikoMember(user=original_interaction.user, client=original_interaction.client)
        self.book = GreenBook(self.u)

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
        res = await self.book.recent_entries
        res_len = len(res)
        async def __default_embed() -> discord.Embed:
            temp = []

            temp.append(
                "The YMCA Green Book for swim tests.\n"
                "This book can be accessed any time in this server "
                f"using {tunables('SLASH_COMMAND_SUGGEST_BOOK')}.\n"
                ""
                "Use the buttons below to search, add, or modify entries "
                "in the green book.\n\n"
            )

            total_entries = await self.book.total_entries
            if res_len > 0: temp.append("__Recent entries__ `[Last Name, First Name]`:")
            else: temp.append("There are no entries in this book. Add one by pressing the  `New Entry`  button.")
            for result in res:
                temp.append(f"\n{result}")
            
            if res_len < total_entries:
                temp.append(f"... and {(total_entries - res_len):,} more\n\n")
            

            embed = discord.Embed(description=''.join(temp), color=GREEN_BOOK_NEUTRAL_COLOR)
            embed.set_author(
                icon_url=self.u.guild.icon,
                name=f"{self.u.guild} Green Book"
            )
            return embed
        
        self.clear_items()
        if res_len > 0: self.add_item(SelectEntries(bview=self, res=res))
        self.add_item(NewEntry(bview=self))
        self.add_item(SearchButton(bview=self))
        if self.u.user.guild_permissions.manage_guild:
            self.add_item(LogChannelButton(bview=self))
        # if admin, add more stuff self.add_item(admin)

        if init: self.msg = await self.original_interaction.original_response()
        await self.msg.edit(
            content=None,
            embed=await __default_embed(),
            view=self
        )