import discord
from Database.database_class import AsyncDatabase
from Database.GuildObjects import MikoMember
from tunables import *
db = AsyncDatabase("misc.log_channels.py")


class ModalTryAgain(discord.ui.View):
    def __init__(self, calling_modal, error_interaction: discord.Interaction):
        super().__init__(timeout=tunables('YMCA_VIEW_TIMEOUT'))
        self.calling_modal = calling_modal
        self.error_interaction = error_interaction

    async def __original_response(self):
        try: self.original_response = await self.error_interaction.original_response()
        except: pass

    @discord.ui.button(style=discord.ButtonStyle.blurple, label="Try Again", custom_id="button_try_again")
    async def try_again(self, interaction: discord.Interaction, button = discord.Button):
        await interaction.response.send_modal(self.calling_modal)
        self.stop()
        await self.__original_response()
        try: await self.original_response.delete()
        except: pass


def check_modal_error(modal) -> dict:
    e = {
        'age': False,
        'wristband': False,
        'type': False,
        'len': False,
        'channel': None
    }
    try: int(modal.age.value)
    except: e['age'] = True

    try: int(modal.chid.value)
    except: e['type'] = True

    try:
        if len(modal.chid.value) < 15: e['len'] = True
    except: pass

    try:
        if not e['type'] and not e['len']:
            e['channel'] = modal.bview.original_interaction.guild.get_channel(int(modal.chid.value))
    except: pass

    try:
        if not e['age']:
            if int(modal.age.value) < 1 or int(modal.age.value) > 100: e['age'] = True
    except: pass

    try:
        if modal.wristband.value.upper() not in ['G', 'Y', 'R', '']:
            e['wristband'] = True
    except: pass

    return e

class LogChannel(discord.ui.View):
    def __init__(self, original_interaction: discord.Interaction, typ: str, return_view):
        super().__init__(timeout=tunables('YMCA_VIEW_TIMEOUT'))
        self.original_interaction = original_interaction
        self.u = MikoMember(user=original_interaction.user, client=original_interaction.client)
        self.return_view = return_view
        self.typ = typ
        self.msg: discord.Message = return_view.msg

    
    async def ainit(self) -> None:
        self.log_channel: discord.TextChannel = ...
        match self.typ:
            case 'GREEN_BOOK':
                self.context = "Swim Test Book"
                self.column = "ymca_green_book_channel"
                self.log_channel = await self.u.ymca_green_book_channel
            case 'SUPPLIES':
                self.context = "Supply Needs"
                self.column = "ymca_supplies_channel"
                self.log_channel = await self.u.ymca_supplies_channel
            case _:
                self.context = None
                self.column = None
                self.log_channel = None
        
        await self.respond_log_channel(t="INIT")
    
    def __log_channel_description(self) -> list:
        temp = []

        if self.log_channel is not None:
            log_channel = self.log_channel.mention
        else: log_channel = "`None`"

        temp.append(
            f"__Current Log channel: {log_channel}\n\n__"
        )

        temp.append(
            "Use the dropdown below to set the channel "
            f"that {self.u.client.user.mention} will send new {self.context} entries "
            "to. Select `Deselect Channel` to remove current channel "
            "(if any)."
            "\n\n"
            "**Note**: If your channel does not appear, it could be "
            f"because {self.u.client.user.mention} does not have `Send Messages` and/or `View Channel` "
            "permissions in that channel."
            "\n\n"
            "Press the `Use ID` "
            "button to choose a channel by pasting in its channel ID. To get "
            "a channel ID, type `#` in chat and begin typing its name. Select "
            "it from the list of channels that pop up and then put a backslash "
            "`\\` in front of it. It will give you something that looks like "
            "`<#1084326524683038880>`. The ID is the numbers and the numbers only."
        )

        return temp
    
    async def respond_log_channel(self, t: str, channel: discord.TextChannel = None) -> None:
        desc = []
        # Embed setup
        match t:
            
            case 'SET':
                send_msg = False
                read_msg = False
                er = []
                try:
                    send_msg = channel.permissions_for(channel.guild.me).send_messages
                    read_msg = channel.permissions_for(channel.guild.me).read_messages
                except: pass
                if not send_msg or not read_msg:
                    if not send_msg: er.append('`Send Messages`')
                    if not read_msg: er.append('`Read Messages`')
                    desc.append(
                        f"❗ **Error: Unable to set channel {channel.mention} as {self.context} log channel. I do not "
                        f"have {' or '.join(er)} "
                        "permissions in that channel.**"
                    )
                    color = GREEN_BOOK_FAIL_COLOR
                else:
                    desc.append(
                        f"✅ **Success! Set {channel.mention} as the {self.context} log channel. "
                        "To unset this channel, press the `Deselect Channel` button.**"
                    )
                    await db.execute(
                        f"UPDATE SERVERS SET {self.column}='{channel.id}' "
                        f"WHERE server_id='{self.original_interaction.guild.id}'"
                    )
                    self.log_channel = channel
                    color = GREEN_BOOK_SUCCESS_COLOR

            case 'DESELECT':
                if self.log_channel is not None:
                    desc.append(
                        f"✅ **Success! {self.log_channel.mention} will no longer receive "
                        f"{self.context} log updates.**"
                    )
                    await db.execute(
                        f"UPDATE SERVERS SET {self.column}=NULL WHERE "
                        f"server_id='{self.original_interaction.guild.id}'"
                    )
                    self.log_channel = None
                    color = GREEN_BOOK_SUCCESS_COLOR
                else:
                    desc.append(
                        f"⚠ Error: There is no active {self.context} log channel."
                    )
                    color = GREEN_BOOK_WARN_COLOR
                
            case _:
                color = GREEN_BOOK_NEUTRAL_COLOR

        desc.append("\n\n")
        desc.append(''.join(self.__log_channel_description()))
        embed = discord.Embed(description=''.join(desc), color=color)
        embed.set_author(icon_url=self.u.guild.icon, name=f"{self.u.guild} {self.context}")

        self.clear_items()
        self.add_item(self.SelectLogChannel())
        self.add_item(self.BackToCallerButton())
        self.add_item(self.UseChannelIDButton())
        d = self.DeselectChannel()
        if self.log_channel is not None: d.disabled=False
        self.add_item(d)

        await self.msg.edit(
            content=None,
            embed=embed,
            view=self
        )
    
    class BackToCallerButton(discord.ui.Button):
        def __init__(self):
            super().__init__(
                style=discord.ButtonStyle.blurple,
                label="Back",
                emoji=None,
                custom_id="back_button",
                row=2
            )

        async def callback(self, interaction: discord.Interaction) -> None:
            await interaction.response.edit_message()
            try: await self.view.return_view.respond()
            except Exception as e: print(e)


    class LogChannelButton(discord.ui.Button):
        def __init__(self):
            super().__init__(
                style=discord.ButtonStyle.blurple,
                label="Log Channel",
                emoji=None,
                custom_id="logc_button",
                row=2
            )

        async def callback(self, interaction: discord.Interaction) -> None:
            await interaction.response.edit_message()
            await self.view.respond_log_channel(t='DEFAULT')



    class UseChannelIDButton(discord.ui.Button):
        def __init__(self):
            super().__init__(
                style=discord.ButtonStyle.gray,
                label="Use ID",
                emoji=None,
                custom_id="id_button",
                row=2
            )

        async def callback(self, interaction: discord.Interaction) -> None:
            await interaction.response.send_modal(self.ChannelIDModal(bview=self.view))

        class ChannelIDModal(discord.ui.Modal):

            def __init__(self, bview):
                super().__init__(title="Enter Channel ID", custom_id="channel_id_modal")
                self.bview = bview

            chid = discord.ui.TextInput(
                    label="Enter Channel ID:",
                    placeholder=f"1084326524683038880",
                    min_length=1,
                    max_length=30
                )
            async def on_submit(self, interaction: discord.Interaction) -> None:
                e = check_modal_error(modal=self)
                if e['type'] or e['len'] or e['channel'] is None: raise Exception
                await interaction.response.edit_message()
                await self.bview.respond_log_channel(t='SET', channel=e['channel'])
            
            async def on_error(self, interaction: discord.Interaction, error) -> None:
                e = check_modal_error(modal=self)
                temp = []
                if e['type']: temp.append("`Channel ID` must be a number")
                if e['len']: temp.append("`Channel ID` must be between 15 and 30 numbers in length.")
                if not e['len'] and not e['type'] and e['channel'] is None:
                    temp.append(f"No channel in this server found with ID `{self.chid.value}`")

                await interaction.response.send_message(
                    content="\n".join(temp),
                    ephemeral=True,
                    view=ModalTryAgain(calling_modal=self, error_interaction=interaction)
                )


    class SelectLogChannel(discord.ui.ChannelSelect):
        def __init__(self):

            super().__init__(
                placeholder="Select a channel",
                min_values=1,
                max_values=1,
                row=1,
                custom_id="select_channel",
                disabled=False,
                channel_types=[
                    discord.ChannelType.text,
                    discord.ChannelType.news
                ]
            )
        
        async def callback(self, interaction: discord.Interaction):
            ch: discord.app_commands.AppCommandChannel = self.values[0]
            try: ch = await ch.fetch()
            except: pass
            await interaction.response.edit_message()
            await self.view.respond_log_channel(t='SET', channel=ch)


    class DeselectChannel(discord.ui.Button):
        def __init__(self):
            super().__init__(
                style=discord.ButtonStyle.red,
                label="Deselect Channel",
                emoji=None,
                custom_id="deselect_button",
                row=2,
                disabled=True
            )

        async def callback(self, interaction: discord.Interaction) -> None:
            await interaction.response.edit_message()
            await self.view.respond_log_channel(t='DESELECT')