import discord
from Database.GuildObjects import MikoMember
from Database.database_class import Database
from Settings.GuildSettings import all_guild_settings
from Settings.UserSettings import all_user_settings
from Settings.embeds import setting_embed, setting_toggled, settings_list, settings_initial
from tunables import tunables
sv = Database("Settings.Views.py")


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
            if await u.manage_guild(): s = all_guild_settings()
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
            self.s[self.i].toggle(server_id=self.original_interaction.guild.id)
            # status = self.s[self.i].value_str(server_id=self.original_interaction.guild.id)
        elif self.s[self.i].table == "USER_SETTINGS":
            self.s[self.i].toggle(user_id=self.original_interaction.user.id)
            # status = self.s[self.i].value_str(user_id=self.original_interaction.user.id)

        embed1 = setting_toggled(u=self.u, s=self.s[self.i])
        embed2 = settings_initial(interaction=self.original_interaction)
        view = SettingsScopeView(original_interaction=self.original_interaction)
        await msg.edit(
            content=None,
            view=view,
            embeds=[embed1, embed2]
        )