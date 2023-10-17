import discord
from misc.view_misc import LogChannel
from tunables import *
from Database.database_class import AsyncDatabase
from Database.GuildObjects import MikoMember
db = AsyncDatabase("ActivityCheck.Introductions.py")


class IntroductionsView(discord.ui.View):
    def __init__(self, original_interaction: discord.Interaction):
        super().__init__(timeout=tunables('GLOBAL_VIEW_TIMEOUT'))
        self.original_interaction = original_interaction
        self.u = MikoMember(user=self.original_interaction.user, client=self.original_interaction.client)
        self.msg: discord.Message = None

    async def ainit(self):
        await self.respond()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.u.user.id

    async def __send_modal(self) -> None:
        await self.original_interaction.response.send_modal(IntroductionModal(u=self.u))

    async def on_timeout(self) -> None:
        try:
            msg = await self.original_interaction.original_response()
            await msg.delete()
        except:
            try:
                await self.msg.delete()
            except: return
    
    async def respond(self) -> None:
        if not await self.u.manage_guild:
            await self.__send_modal()
            return
        
        self.clear_items()
        self.add_item(SelectIntroductionRole())
        
        t = ToggleIntroductions(u=self.u)
        s = discord.ButtonStyle
        role = await self.u.introduction_role
        ch = await self.u.introductions_channel
        status = await self.u.introductions_required
        t.disabled = ch is None or role is None
        t.style = s.red if not status else s.green
        t.label = "Disabled" if ch is None or not status else "Enabled"
        self.add_item(t)
        
        self.add_item(LogChannelButton())
        
        si = SendIntroduction()
        si.disabled = t.disabled
        self.add_item(si)
        
        if self.msg is None:
            await self.original_interaction.response.send_message(content=tunables('LOADING_EMOJI'), ephemeral=True)
            self.msg = await self.original_interaction.original_response()
        
        desc = []
        desc.append(
            "# Use the buttons below to "
            "toggle introduction requirements and what channel to "
            "send introductions to.\n"
            
            "__Current introduction role__: "
            f"{role.mention if role is not None else '`None`'}\n\n"
            
            "Note: Must select a channel to send introductions "
            "to before enabling introductions."
        )
        
        embed = discord.Embed(description=''.join(desc), color=GLOBAL_EMBED_COLOR)
        embed.set_author(
            name="Introductions Admin Page",
            icon_url=self.u.guild.icon.url
        )
        
        await self.msg.edit(
            content=None,
            view=self,
            embed=embed
        )
        
        
class SendIntroduction(discord.ui.Button):

    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.green,
            label="Create introduction",
            custom_id="intro_button",
            row=2
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(IntroductionModal(u=self.view.u))
            
        
class LogChannelButton(discord.ui.Button):

    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.blurple,
            label="Log Channel",
            custom_id="logcfdjic_button",
            row=2
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await LogChannel(
                original_interaction=interaction,
                typ="INTRODUCTIONS",
                return_view=self.view
            ).ainit()
        
class ToggleIntroductions(discord.ui.Button):

    def __init__(self, u: MikoMember):
        self.u = u
        super().__init__(
            style=discord.ButtonStyle.gray,
            label="()",
            custom_id="toggle_intro_button",
            row=2
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await self.u.toggle_introductions()
        await self.view.respond()

class SelectIntroductionRole(discord.ui.RoleSelect):
    def __init__(self):

        super().__init__(
            placeholder="Select role",
            min_values=0,
            max_values=1,
            row=1,
            custom_id="select_roles",
            disabled=False
        )
    
    async def callback(self, interaction: discord.Interaction):
        role = self.values
        await interaction.response.edit_message()
        
        if role == []: s = "NULL"
        else: role = s = f"'{role[0].id}'"
        
        await db.execute(
            f"UPDATE SERVERS SET introductions_role={s} WHERE "
            f"server_id='{interaction.guild.id}'"
        )
        await self.view.respond()

class IntroductionModal(discord.ui.Modal):

    def __init__(self, u: MikoMember):
        self.u = u
        super().__init__(title="Introduce Yourself", custom_id="introductions")

    name = discord.ui.TextInput(
            label="Name:",
            placeholder="Jefferson Andrade",
            min_length=1,
            max_length=50,
            default=None
        )
    
    nickname = discord.ui.TextInput(
            label="Nickname (leave blank for none):",
            placeholder="Lisa Enthusiast",
            min_length=1,
            max_length=20,
            default=None,
            required=False
        )
    
    pronouns = discord.ui.TextInput(
            label="Pronouns (leave blank for no preference):",
            placeholder="He/Him",
            min_length=1,
            max_length=10,
            default=None,
            required=False
        )

    major = discord.ui.TextInput(
            label="Major:",
            placeholder="Physics",
            min_length=0,
            max_length=50,
            required=True,
            default=None
        )

    other_info = discord.ui.TextInput(
            label="3 things about you and how did you find us?",
            # placeholder="",
            min_length=0,
            max_length=tunables('INTRODUCTIONS_MAX_OTHER_INFO'),
            required=True,
            default=None,
            style=discord.TextStyle.paragraph
        )
    async def on_submit(self, interaction: discord.Interaction) -> None:
        channel = await self.u.introductions_channel
        try: await interaction.response.edit_message()
        except: await interaction.response.send_message(
            content=f"Introduction received. View it in {channel.mention}",
            ephemeral=True
        )
        
        desc = []
        
        desc.append(
            f"**User**: {interaction.user.mention}\n"
            f"**Name**: {self.name.value}\n"
            f"**Nickname**: {self.nickname.value if self.nickname.value != '' else 'N/A'}\n"
            f"**Pronouns**: {self.pronouns.value if self.pronouns.value != '' else 'N/A'}\n"
            f"**Major**: {self.major.value}\n"
            f"**Extra info**: {self.other_info.value}"
            "\n\n"
            "Introduce yourself to gain access to the\n"
            "rest of the server using "
            f"{tunables('SLASH_COMMAND_SUGGEST_INTRODUCTIONS')}"
        )
        
        
        embed = discord.Embed(
            description=''.join(desc),
            color=GLOBAL_EMBED_COLOR
        )
        
        embed.set_author(
            name=interaction.user.name,
            icon_url=interaction.user.avatar
        )
        
        await interaction.user.add_roles(await self.u.introduction_role)
        
        await channel.send(
            content=None,
            embed=embed
        )
    
    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        pass