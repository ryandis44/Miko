import discord
from Settings.ChannelSettings import all_channel_settings
from Settings.GuildSettings import all_guild_settings
from Settings.UserSettings import all_user_settings
from Settings.settings import Setting, MikoMember
from tunables import *


# Main settings class responsible for entire settings menu interaction
class SettingsView(discord.ui.View):
    def __init__(self, original_interaction: discord.Interaction) -> None:
        super().__init__(timeout=tunables('GLOBAL_VIEW_TIMEOUT'))
        self.original_interaction = original_interaction
        self.scope = {'type': None, 'data': [], 'len': 0}
        self.offset = 0

    @property
    def channel(self) -> discord.TextChannel:
        return self.original_interaction.channel if \
            self.scope['type'] == "CHANNELS" else None
    @property
    def channel_id(self) -> int:
        if self.channel is None: return None
        return self.channel.id

    async def ainit(self) -> None:
        self.u = MikoMember(user=self.original_interaction.user, client=self.original_interaction.client)
        await self.u.ainit()
        self.msg = await self.original_interaction.original_response()
        await self.main_page()

    async def on_timeout(self) -> None:
        try: await self.msg.delete()
        except: pass

    async def main_page(self) -> None:
        temp = []
        temp.append(
            f"Most {self.u.client.user.mention} Commands and features can\n"
            "be toggled at any time using this menu."
            "\n\n"
            "__**Select which settings to modify**__:\n\n"
            f"• {tunables('SETTINGS_UI_USER_EMOJI')} **Yourself**: Change settings that affect only you (not guild-specific)"
            "\n\n"
            f"• {tunables('SETTINGS_UI_CHANNEL_EMOJI')} **Channel**: Change settings that affect this channel\n"
            "Note: Must have `Mange Channel` permission in this channel to modify these settings."
            "\n\n"
            f"• {tunables('SETTINGS_UI_GUILD_EMOJI')} **Guild**: Change settings that affect all users in this guild.\n"
            "Note: Must have `Manage Server` permission to modify these settings."
        )
        
        embed = discord.Embed(color=GLOBAL_EMBED_COLOR, description=''.join(temp))
        embed.set_author(icon_url=self.u.client.user.avatar, name=f"{self.u.client.user.name} Settings")
        
        self.clear_items()
        self.add_item(ChooseScope(miko_user=self.u.client.user.name))
        await self.msg.edit(content=None, view=self, embed=embed)

    async def __set_scope(self, interaction: discord.Interaction) -> None:
        self.offset = 0
        match self.scope['type']:
            
            case 'SERVERS':
                if not await self.u.manage_guild:
                    await interaction.response.send_message(
                        content=tunables('SETTINGS_UI_NO_PERMISSION_GUILD'), ephemeral=True
                    )
                    return
                self.scope['data'] = all_guild_settings(u=self.u, p=await self.u.profile)
                self.scope['len'] = len(self.scope['data'])
            
            case 'CHANNELS':
                if not await self.u.manage_channel(channel=interaction.channel):
                    await interaction.response.send_message(
                        content=tunables('SETTINGS_UI_NO_PERMISSION_CHANNEL'), ephemeral=True
                    )
                    return
                self.scope['data'] = all_channel_settings(u=self.u, p=await self.u.profile)
                self.scope['len'] = len(self.scope['data'])
            
            case _:
                self.scope['data'] = all_user_settings(u=self.u, p=await self.u.profile)
                self.scope['len'] = len(self.scope['data'])

    async def settings_list_page(self, interaction: discord.Interaction, initial=False) -> None:
        if initial: await self.__set_scope(interaction=interaction)
        
        await interaction.response.edit_message()
        temp = ["__Select a setting to modify"]
        
        if self.scope['type'] == "CHANNELS": temp.append(
            f" for {self.channel.mention}__:\n\n"
        )
        else: temp.append("__:\n\n")
        
        for setting in self.scope['data'][self.offset:self.offset+tunables('SETTINGS_UI_MAX_SETTINGS_LISTABLE')]:
            setting: Setting
            temp.append(
                "• "
                f"{setting.emoji} "
                f"`{setting.name}`: "
                f"*{setting.desc}*"
                f"{await setting.value_str(channel_id=self.channel_id)}"
                "\n"
            )
        
        embed = discord.Embed(color=GLOBAL_EMBED_COLOR, description=''.join(temp))
        embed.set_author(
            icon_url=await self.u.user_avatar if self.scope['type'] == "USER_SETTINGS" else self.u.guild.icon,
            name=f"{await self.u.username if self.scope['type'] == 'USER_SETTINGS' else self.u.guild.name} Settings"
        )
        
        self.clear_items()
        self.add_item(ChooseSetting(settings=self.scope['data'][self.offset:self.offset+tunables('SETTINGS_UI_MAX_SETTINGS_LISTABLE')]))
        self.add_item(BackToHome())
        if self.scope['len'] > 5:
            if self.offset > 0:
                self.add_item(PrevButton(disabled=False))
            else:
                self.add_item(PrevButton(disabled=True))
            if self.scope['len'] > self.offset + tunables('SETTINGS_UI_MAX_SETTINGS_LISTABLE') and self.scope['len'] > \
                tunables('SETTINGS_UI_MAX_SETTINGS_LISTABLE'):
                    self.add_item(NextButton(disabled=False))
            else:
                self.add_item(NextButton(disabled=True))
        
        
        await self.msg.edit(content=None, view=self, embed=embed)
        
    async def setting_page(self, s: Setting) -> None:
        temp = []
        if self.scope['type'] == "CHANNELS":
            msg = f" *in* {self.channel.mention}"
        else: msg = ""
        temp.append(
            "• "
            f"{s.emoji} "
            f"`{s.name}`: "
            f"*{s.desc}*{msg}"
            "\n\n"
            "**You currently have this setting set to**:\n"
            f"{await s.value_str(channel_id=self.channel_id)}\n"
            "If you would like to change it, use the dropdown below."
        )
        
        embed = discord.Embed(color=GLOBAL_EMBED_COLOR, description=''.join(temp), title="You are choosing to modify the following setting:")
        embed.set_author(
            icon_url=await self.u.user_avatar if self.scope['type'] == "USER_SETTINGS" else self.u.guild.icon,
            name=f"{await self.u.username if self.scope['type'] == 'USER_SETTINGS' else self.u.guild.name} Settings"
        )
        
        self.clear_items()
        self.add_item(ChooseState(setting=s))
        self.add_item(BackToHome())
        await self.msg.edit(content=None, view=self, embed=embed)
    
    async def setting_state_choice(self, interaction: discord.Interaction, s: Setting, choice) -> None:
        u = MikoMember(user=interaction.user, client=interaction.client)
        check = True
        match self.scope['type']:
            case "CHANNELS":
                if not await u.manage_channel(channel=self.channel): check = False
                msg = tunables('SETTINGS_UI_NO_PERMISSION_CHANNEL')
            case "SERVERS":
                if not await u.manage_guild: check = False
                msg = tunables('SETTINGS_UI_NO_PERMISSION_GUILD')
        
        if not check:
            await interaction.response.send_message(content=msg, ephemeral=True)
            return
    
        await interaction.response.edit_message()
        await s.set_state(state=choice, channel_id=self.channel_id)
    
        self.clear_items()
        await self.setting_page(s=s)
    
    

# Class responsible for listing setting scopes
class ChooseScope(discord.ui.Select):
    def __init__(self, miko_user: str):
        options = [
            discord.SelectOption(
                label="Yourself",
                description=f"Modify your personal {miko_user} settings",
                value="USER_SETTINGS",
                emoji=tunables('SETTINGS_UI_USER_EMOJI')
            ),
            discord.SelectOption(
                label="Channel",
                description=f"Modify {miko_user} settings for this Channel",
                value="CHANNELS",
                emoji=tunables('SETTINGS_UI_CHANNEL_EMOJI')
            ),
            discord.SelectOption(
                label="Guild",
                description=f"Modify {miko_user} settings for this Guild",
                value="SERVERS",
                emoji=tunables('SETTINGS_UI_GUILD_EMOJI')
            )
        ]
            
        super().__init__(placeholder="Select a category", max_values=1, min_values=1, options=options)
    
    async def callback(self, interaction: discord.Interaction):
        self.view.scope['type'] = self.values[0]
        await self.view.settings_list_page(interaction=interaction, initial=True)

# Class responsible for listing individual settings
class ChooseSetting(discord.ui.Select):
    def __init__(self, settings: list) -> None:
        options = []
        for i, setting in enumerate(settings):
            setting: Setting
            options.append(
                discord.SelectOption(
                    label=f"{setting.name}",
                    value=i,
                    emoji=setting.emoji
                )
            )
        super().__init__(placeholder="Select a setting", max_values=1, min_values=1, options=options, row=1)
    
    async def callback(self, interaction: discord.Interaction) -> None:
        setting = self.view.scope['data'][int(self.values[0])]
        await interaction.response.edit_message()
        await self.view.setting_page(setting)

class ChooseState(discord.ui.Select):
    def __init__(self, setting: Setting) -> None:
        self.s = setting
        super().__init__(
            placeholder="Select an option",
            max_values=1,
            min_values=1,
            options=setting.options,
            row=1,
            disabled=not setting.modifiable['val']
        )
    async def callback(self, interaction: discord.Integration) -> None:
        val = self.values[0]
        await self.view.setting_state_choice(interaction, self.s, val)

# Simple back to home button
class BackToHome(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.gray,
            label="Back",
            emoji=None,
            custom_id="back_button",
            row=2
        )
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await self.view.main_page()

# Responsible for handling moving back a page
class PrevButton(discord.ui.Button):
    def __init__(self, disabled: bool=False) -> None:
        super().__init__(
            style=discord.ButtonStyle.gray,
            label=None,
            emoji=tunables('GENERIC_PREV_BUTTON'),
            custom_id="prev_button",
            row=2,
            disabled=disabled
        )
    async def callback(self, interaction: discord.Interaction) -> None:
        if self.view.offset <= tunables('SETTINGS_UI_MAX_SETTINGS_LISTABLE'): self.view.offset = 0
        elif self.offset > self.offset - tunables('SETTINGS_UI_MAX_SETTINGS_LISTABLE'): \
            self.view.offset -= tunables('SETTINGS_UI_MAX_SETTINGS_LISTABLE')
        else: return
        await self.view.settings_list_page(interaction)
        
# Responsible for handling moving forward a page
class NextButton(discord.ui.Button):
    def __init__(self, disabled: bool=False) -> None:
        super().__init__(
            style=discord.ButtonStyle.gray,
            label=None,
            emoji=tunables('GENERIC_NEXT_BUTTON'),
            custom_id="next_button",
            row=2,
            disabled=disabled
        )
    async def callback(self, interaction: discord.Interaction) -> None:
        if self.view.scope['len'] > self.view.offset + (tunables('SETTINGS_UI_MAX_SETTINGS_LISTABLE') * 2): \
            self.view.offset += tunables('SETTINGS_UI_MAX_SETTINGS_LISTABLE')
        elif self.view.scope['len'] <= self.view.offset + (tunables('SETTINGS_UI_MAX_SETTINGS_LISTABLE') * 2): \
            self.view.offset = self.view.scope['len'] - tunables('SETTINGS_UI_MAX_SETTINGS_LISTABLE')
        else: return
        await self.view.settings_list_page(interaction)
        
