import discord
from Settings.ChannelSettings import all_channel_settings
from Settings.GuildSettings import all_guild_settings
from Settings.UserSettings import all_user_settings
from Settings.embeds import setting_embed, setting_toggled, settings_list, settings_initial
from Settings.settings import Setting, MikoMember
from tunables import *


# Main settings class responsible for entire settings menu interaction
class SettingsView(discord.ui.View):
    def __init__(self, original_interaction: discord.Interaction) -> None:
        super().__init__(timeout=tunables('GLOBAL_VIEW_TIMEOUT'))
        self.original_interaction = original_interaction
        self.scope = {'type': None, 'data': []}
        self.offset = {'data': 0, 'prev': False, 'next': True}

    @property
    def channel(self) -> discord.TextChannel:
        return self.original_interaction.channel if \
            self.scope['type'] == "CHANNELS" else None

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

    async def settings_list_page(self, interaction: discord.Interaction) -> None:
        match self.scope['type']:
            
            case 'SERVERS':
                if not await self.u.manage_guild:
                    await interaction.response.send_message(
                        content=tunables('SETTINGS_UI_NO_PERMISSION_GUILD'), ephemeral=True
                    )
                    return
                self.scope['data'] = all_guild_settings(u=self.u)
            
            case 'CHANNELS':
                if not await self.u.manage_channel(channel=interaction.channel):
                    await interaction.response.send_message(
                        content=tunables('SETTINGS_UI_NO_PERMISSION_CHANNEL'), ephemeral=True
                    )
                    return
                self.scope['data'] = all_channel_settings(u=self.u)
            
            case _: self.scope['data'] = all_user_settings(u=self.u)
        
        await interaction.response.edit_message()
        temp = ["__Select a setting to modify__:\n\n"]
        
        for setting in self.scope['data']:
            setting: Setting
            temp.append(
                "• "
                f"{setting.emoji} "
                f"`{setting.name}`: "
                f"*{setting.desc}*"
                f"{await setting.value_str(channel_id=self.channel.id)}"
                "\n"
            )
        
        embed = discord.Embed(color=GLOBAL_EMBED_COLOR, description=''.join(temp))
        embed.set_author(
            icon_url=await self.u.user_avatar if self.scope['type'] == "USER_SETTINGS" else self.u.guild.icon,
            name=f"{await self.u.username if self.scope['type'] == 'USER_SETTINGS' else self.u.guild.name} Settings"
        )
        
        self.clear_items()
        self.add_item(ChooseSetting(settings=self.scope['data']))
        self.add_item(BackToHome())
        
        await self.msg.edit(content=None, view=self, embed=embed)
        
    async def setting_page(self, s: Setting) -> None:
        print(s)
        temp = []
        temp.append(
            "• "
            f"{s.emoji} "
            f"`{s.name}`: "
            f"*{s.desc}*"
            "\n\n"
            "**You currently have this setting set to**:\n"
            f"{await s.value_str(channel_id=self.channel.id)}\n"
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
        check = True
        match self.scope['type']:
            case "CHANNELS":
                if not self.u.manage_channel(channel=self.channel): check = False
            case "SERVERS":
                if not self.u.manage_guild: check = False
        
        if not check:
            await interaction.response.send_message(
                content=tunables('SETTINGS_UI_NO_PERMISSION_CHANNEL'), ephemeral=True
            )
            return
    
        await s.set_state(state=choice, channel_id=self.channel.id)
    
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

        await self.view.settings_list_page(interaction=interaction)

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
            placeholder="Select a setting",
            max_values=1,
            min_values=1,
            options=setting.options,
            row=1
        )
    async def callback(self, interaction: discord.Integration) -> None:
        val = self.values[0]
        await self.view.setting_state_choice(self.s, val)

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
    def __init__(self) -> None:
        super().__init__(
            style=discord.ButtonStyle.gray,
            label=None,
            emoji=tunables('GENERIC_PREV_BUTTON'),
            custom_id="prev_button",
            row=2
        )
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()

# Responsible for handling moving forward a page
class NextButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(
            style=discord.ButtonStyle.gray,
            label=None,
            emoji=tunables('GENERIC_NEXT_BUTTON'),
            custom_id="next_button",
            row=2
        )
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()







class SettingsScopeView(discord.ui.View):
    
    def __init__(self, original_interaction: discord.Interaction):
        super().__init__(timeout=tunables('GLOBAL_VIEW_TIMEOUT'))
        self.add_item(SettingsScopeDropdown(original_interaction=original_interaction))
        self.original_interaction = original_interaction
    
    # Only the user that ran the command to press buttons
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.original_interaction.user

class SettingsScopeDropdown(discord.ui.Select):
    def __init__(self, original_interaction: discord.Interaction):
        self.original_interaction = original_interaction

        options = []
        options.append(
            discord.SelectOption(
                label="Yourself",
                description="Modify your personal Miko settings",
                value=0,
                emoji="🙋‍♂️"
            )
        )
        options.append(
            discord.SelectOption(
                label="Guild",
                description="Modify Miko Guild settings",
                value=1,
                emoji="🛡"
            )
        )
            
        super().__init__(placeholder="Select an option", max_values=1, min_values=1, options=options)
    async def callback(self, interaction: discord.Interaction):

        msg = await self.original_interaction.original_response()
        u = MikoMember(user=interaction.user, client=interaction.client)
        await u.ainit()
        i = int(self.values[0])

        if i == 0: s = all_user_settings()
        else:
            if await u.manage_guild: s = all_guild_settings()
            else:
                await interaction.response.send_message(
                    content=(
                        ":exclamation: You must have the `Manage Server` permission to "
                        "change these settings. Contact the guild owner or "
                        "a guild admin if this is an error."
                    ),
                    ephemeral=True
                )
                return

        await interaction.response.edit_message()
        view = ScopeSettingsView(original_interaction=self.original_interaction, s=s, u=u)
        await msg.edit(embed=await settings_list(u=u, settings=s[0:5]), view=view)


class ScopeSettingsView(discord.ui.View):
    def __init__(self, original_interaction: discord.Interaction, s: list, u: MikoMember):
        super().__init__(timeout=tunables('GLOBAL_VIEW_TIMEOUT'))
        self.add_item(ScopeSettingsDropdown(original_interaction=original_interaction, s=s, u=u))
        self.original_interaction = original_interaction
        self.s = s
        self.u = u
        self.limit = 5
        self.offset = 0
        self.amount = len(s)
        self.button_presence()

    def button_presence(self):
        back: discord.Button = [x for x in self.children if x.custom_id=="back"][0]
        prev: discord.Button = [x for x in self.children if x.custom_id=="prev"][0]
        next: discord.Button = [x for x in self.children if x.custom_id=="next"][0]

        back.disabled = False
        if self.offset > 0:
            prev.disabled = False
        else:
            prev.disabled = True
        
        if self.amount > self.offset + self.limit and self.amount > 5:
            next.disabled = False
        else:
            next.disabled = True
    
    
    @discord.ui.button(style=discord.ButtonStyle.gray, label="Back", emoji=None, custom_id="back", disabled=True, row=2)
    async def back_callback(self, interaction: discord.Interaction, button = discord.Button):
        await interaction.response.edit_message()
        msg = await self.original_interaction.original_response()
        await msg.edit(
            view = SettingsScopeView(original_interaction=self.original_interaction),
            content=None,
            embed=settings_initial(self.original_interaction)
        )

    @discord.ui.button(style=discord.ButtonStyle.gray, label=None, emoji=tunables('GENERIC_PREV_BUTTON'), custom_id="prev", disabled=True, row=2)
    async def prev_callback(self, interaction: discord.Interaction, button = discord.Button):
        if self.offset <= self.limit: self.offset = 0
        elif self.offset > self.offset - self.limit: self.offset -= self.limit
        else: return
        self.button_presence()
        await interaction.response.edit_message()
        msg = await self.original_interaction.original_response()
        await msg.edit(
            view=self,
            content=None,
            embed=await settings_list(u=self.u, settings=self.s[self.offset:self.offset + 5])
        )
    
    @discord.ui.button(style=discord.ButtonStyle.gray, label=None, emoji=tunables('GENERIC_NEXT_BUTTON'), custom_id="next", disabled=True, row=2)
    async def next_callback(self, interaction: discord.Interaction, button = discord.Button):
        if self.amount > self.offset + (self.limit * 2): self.offset += self.limit
        elif self.amount <= self.offset + (self.limit * 2): self.offset = self.amount - self.limit
        else: return
        self.button_presence()
        await interaction.response.edit_message()
        msg = await self.original_interaction.original_response()
        await msg.edit(
            view=self,
            content=None,
            embed=await settings_list(u=self.u, settings=self.s[self.offset:self.offset + 5])
        )
    
    # @discord.ui.button(style=discord.ButtonStyle.gray, emoji=tunables('GENERIC_NEXT_BUTTON'), custom_id="next")
    # async def forward_callback(self, interaction: discord.Interaction, button = discord.Button):
    #     # if 17 > 0 + 20 == False
    #     if self.updates > self.offset + (self.limit * 2): self.offset += self.limit
    #     # If 17 <= 0 + 20 == True
    #     elif self.updates <= self.offset + (self.limit * 2): self.offset = self.updates - self.limit
    #     else: return
    #     self.button_presence()
    #     await interaction.response.edit_message()
    #     msg = await interaction.original_response()
    #     await msg.edit(content=tunables('PLAYTIME_CONTENT_MSG'), embed=playtime_embed(self.user, self.limit, updates=self.updates,
    #         offset=self.offset, playtime=self.playtime, avg_session=self.avg), view=self)
    
    # @discord.ui.button(style=discord.ButtonStyle.gray, emoji=tunables('GENERIC_LAST_BUTTON'), custom_id="end")
    # async def end_callback(self, interaction: discord.Interaction, button = discord.Button):
    #     self.offset = self.updates - self.limit
    #     self.button_presence()
    #     await interaction.response.edit_message()
    #     msg = await interaction.original_response()
    #     await msg.edit(content=tunables('PLAYTIME_CONTENT_MSG'), embed=playtime_embed(self.user, self.limit, updates=self.updates,
    #         offset=self.offset, playtime=self.playtime, avg_session=self.avg), view=self)

    # Only the user that ran the command to press buttons
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.original_interaction.user

class ScopeSettingsDropdown(discord.ui.Select):
    def __init__(self, original_interaction: discord.Interaction, s: list, u: MikoMember):
        self.original_interaction = original_interaction
        self.s = s
        self.u = u

        options = []
        for i, setting in enumerate(s):
            options.append(
                discord.SelectOption(
                    label=f"{setting.name}",
                    # description=,
                    value=i,
                    emoji=setting.emoji
                )
            )
            
        super().__init__(placeholder="Select an option", max_values=1, min_values=1, options=options, row=1)
    async def callback(self, interaction: discord.Interaction):

        await interaction.response.edit_message()
        msg = await self.original_interaction.original_response()
        i = int(self.values[0])

        embed = await setting_embed(u=self.u, s=self.s[i])
        view = ToggleSettingView(original_interaction=self.original_interaction, s=self.s, u=self.u, i=i)
        await msg.edit(content=None, embed=embed, view=view)


class ToggleSettingView(discord.ui.View):
    def __init__(self, original_interaction: discord.Interaction, s: list, u: MikoMember, i: int):
        super().__init__(timeout=tunables('GLOBAL_VIEW_TIMEOUT'))
        self.original_interaction = original_interaction
        self.s = s
        self.u = u
        self.i = i
        self.button_presence()

    def button_presence(self):
        confirm: discord.Button = [x for x in self.children if x.custom_id=="confirm"][0]
        if self.s[self.i].toggleable: confirm.disabled = False
    
    @discord.ui.button(style=discord.ButtonStyle.red, label="Cancel", custom_id="cancel", disabled=False)
    async def cancel_callback(self, interaction: discord.Interaction, button = discord.Button):
        await interaction.response.edit_message()
        msg = await self.original_interaction.original_response()
        await msg.delete()

    @discord.ui.button(style=discord.ButtonStyle.green, label="Confirm", custom_id="confirm", disabled=True)
    async def confirm_callback(self, interaction: discord.Interaction, button = discord.Button):
        await interaction.response.edit_message()
        msg = await self.original_interaction.original_response()
        await self.u.increment_statistic('SETTINGS_CHANGED')


        if self.s[self.i].table == "SERVERS":
            await self.s[self.i].toggle(server_id=self.original_interaction.guild.id)
            # status = self.s[self.i].value_str(server_id=self.original_interaction.guild.id)
        elif self.s[self.i].table == "USER_SETTINGS":
            await self.s[self.i].toggle(user_id=self.original_interaction.user.id)
            # status = self.s[self.i].value_str(user_id=self.original_interaction.user.id)

        embed1 = await setting_toggled(u=self.u, s=self.s[self.i])
        embed2 = settings_initial(interaction=self.original_interaction)
        view = SettingsScopeView(original_interaction=self.original_interaction)
        await msg.edit(
            content=None,
            view=view,
            embeds=[embed1, embed2]
        )