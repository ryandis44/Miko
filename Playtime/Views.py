import time
import discord
from discord.ui import View
import typing
from Database.database_class import Database
from tunables import *
from misc.embeds import modified_playtime_embed
from Playtime.playtime import avg_playtime_result, get_total_activity_updates, get_total_activity_updates_query, playtime_embed, total_playtime_result

ptv = Database("Playtime.Views.py")

class PlaytimePageSelector(View):
    
    '''
    This view works by allowing the user to advance to the next page
    if there is a next page (based off of self.updates). It will also
    let the user go to the previous page (offset) if there is one.
    
    When there is not a previos or next page, the individual buttons
    are disabled/enabled by the button_presence() function
    '''
    
    def __init__(self, author, user, limit, updates, playtime=[], avg_session="None"):
        super().__init__(timeout=120)
        self.author = author
        self.user = user
        self.limit = limit
        self.offset = 0
        self.updates = updates
        self.playtime = playtime
        self.avg = avg_session
    

    def button_presence(self):
        front = [x for x in self.children if x.custom_id=="front"][0]
        back = [x for x in self.children if x.custom_id=="back"][0]
        next = [x for x in self.children if x.custom_id=="next"][0]
        end = [x for x in self.children if x.custom_id=="end"][0]

        if self.offset > 0:
            front.disabled = False
            back.disabled = False
        else:
            front.disabled = True
            back.disabled = True
        
        if self.updates > self.offset + self.limit:
            next.disabled = False
            end.disabled = False
        else:
            next.disabled = True
            end.disabled = True
    
    
    @discord.ui.button(style=discord.ButtonStyle.gray, emoji=tunables('GENERIC_FIRST_BUTTON'), custom_id="front", disabled=True)
    async def front_callback(self, interaction: discord.Interaction, button = discord.Button):
        self.offset = 0
        self.button_presence()
        await interaction.response.edit_message()
        msg = await interaction.original_response()
        await msg.edit(content=tunables('PLAYTIME_CONTENT_MSG'), embed=playtime_embed(self.user, self.limit, updates=self.updates,
            offset=self.offset, playtime=self.playtime, avg_session=self.avg), view=self)

    @discord.ui.button(style=discord.ButtonStyle.gray, emoji=tunables('GENERIC_PREV_BUTTON'), custom_id="back", disabled=True)
    async def back_callback(self, interaction: discord.Interaction, button = discord.Button):
        # If 8 <= 10
        if self.offset <= self.limit: self.offset = 0 
        # If 8 > 8 - 10
        elif self.offset > self.offset - self.limit: self.offset -= self.limit
        else: return
        self.button_presence()
        await interaction.response.edit_message()
        msg = await interaction.original_response()
        await msg.edit(content=tunables('PLAYTIME_CONTENT_MSG'), embed=playtime_embed(self.user, self.limit, updates=self.updates,
            offset=self.offset, playtime=self.playtime, avg_session=self.avg), view=self)
    
    @discord.ui.button(style=discord.ButtonStyle.gray, emoji=tunables('GENERIC_NEXT_BUTTON'), custom_id="next")
    async def forward_callback(self, interaction: discord.Interaction, button = discord.Button):
        # if 17 > 0 + 20 == False
        if self.updates > self.offset + (self.limit * 2): self.offset += self.limit
        # If 17 <= 0 + 20 == True
        elif self.updates <= self.offset + (self.limit * 2): self.offset = self.updates - self.limit
        else: return
        self.button_presence()
        await interaction.response.edit_message()
        msg = await interaction.original_response()
        await msg.edit(content=tunables('PLAYTIME_CONTENT_MSG'), embed=playtime_embed(self.user, self.limit, updates=self.updates,
            offset=self.offset, playtime=self.playtime, avg_session=self.avg), view=self)
    
    @discord.ui.button(style=discord.ButtonStyle.gray, emoji=tunables('GENERIC_LAST_BUTTON'), custom_id="end")
    async def end_callback(self, interaction: discord.Interaction, button = discord.Button):
        self.offset = self.updates - self.limit
        self.button_presence()
        await interaction.response.edit_message()
        msg = await interaction.original_response()
        await msg.edit(content=tunables('PLAYTIME_CONTENT_MSG'), embed=playtime_embed(self.user, self.limit, updates=self.updates,
            offset=self.offset, playtime=self.playtime, avg_session=self.avg), view=self)
    
    # Only the user that ran the command to press buttons
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.author

class PlaytimeSearchPageSelector(View):
    '''
    This view works by allowing the user to advance to the next page
    if there is a next page (based off of self.updates). It will also
    let the user go to the previous page (offset) if there is one.
    
    When there is not a previos or next page, the individual buttons
    are disabled/enabled by the button_presence() function
    '''
    
    def __init__(self, author, user, game, sort, limit, updates, query, scope, result, total, avg):
        super().__init__(timeout=120)
        self.author = author
        self.user = user
        self.limit = limit
        self.updates = updates
        self.game = game
        self.sort = sort
        self.scope = scope
        self.offset = 0
        self.query = ''.join(query)
        self.result = result
        self.total = total
        self.avg = avg
    

    def button_presence(self):
        front = [x for x in self.children if x.custom_id=="front"][0]
        back = [x for x in self.children if x.custom_id=="back"][0]
        next = [x for x in self.children if x.custom_id=="next"][0]
        end = [x for x in self.children if x.custom_id=="end"][0]

        if self.offset > 0:
            front.disabled = False
            back.disabled = False
        else:
            front.disabled = True
            back.disabled = True
        
        if self.updates > self.offset + self.limit:
            next.disabled = False
            end.disabled = False
        else:
            next.disabled = True
            end.disabled = True
    
    
    @discord.ui.button(style=discord.ButtonStyle.gray, emoji=tunables('GENERIC_FIRST_BUTTON'), custom_id="front", disabled=True)
    async def front_callback(self, interaction: discord.Interaction, button = discord.Button):
        self.offset = 0
        self.button_presence()
        await interaction.response.edit_message()
        msg = await interaction.original_response()
        await msg.edit(content=tunables('PLAYTIME_CONTENT_MSG'), embed=modified_playtime_embed(
            self.user, self.game, self.result[self.offset:self.offset+self.limit],
            self.sort, self.limit, self.updates,
            offset=self.offset, scope=self.scope,
            total=self.total, avg=self.avg),
            view=self)

    @discord.ui.button(style=discord.ButtonStyle.gray, emoji=tunables('GENERIC_PREV_BUTTON'), custom_id="back", disabled=True)
    async def back_callback(self, interaction: discord.Interaction, button = discord.Button):
        # If 8 <= 10
        if self.offset <= self.limit: self.offset = 0 
        # If 8 > 8 - 10
        elif self.offset > self.offset - self.limit: self.offset -= self.limit
        else: return
        self.button_presence()
        await interaction.response.edit_message()
        msg = await interaction.original_response()
        await msg.edit(content=tunables('PLAYTIME_CONTENT_MSG'), embed=modified_playtime_embed(
            self.user, self.game, self.result[self.offset:self.offset+self.limit],
            self.sort, self.limit, self.updates,
            offset=self.offset, scope=self.scope,
            total=self.total, avg=self.avg),
            view=self)
    
    @discord.ui.button(style=discord.ButtonStyle.gray, emoji=tunables('GENERIC_NEXT_BUTTON'), custom_id="next")
    async def forward_callback(self, interaction: discord.Interaction, button = discord.Button):
        # if 17 > 0 + 20 == False
        if self.updates > self.offset + (self.limit * 2): self.offset += self.limit
        # If 17 <= 0 + 20 == True
        elif self.updates <= self.offset + (self.limit * 2): self.offset = self.updates - self.limit
        else: return
        self.button_presence()
        await interaction.response.edit_message()
        msg = await interaction.original_response()
        await msg.edit(content=tunables('PLAYTIME_CONTENT_MSG'), embed=modified_playtime_embed(
            self.user, self.game, self.result[self.offset:self.offset+self.limit],
            self.sort, self.limit, self.updates,
            offset=self.offset, scope=self.scope,
            total=self.total, avg=self.avg),
            view=self)

    
    @discord.ui.button(style=discord.ButtonStyle.gray, emoji=tunables('GENERIC_LAST_BUTTON'), custom_id="end")
    async def end_callback(self, interaction: discord.Interaction, button = discord.Button):
        self.offset = self.updates - self.limit
        self.button_presence()
        await interaction.response.edit_message()
        msg = await interaction.original_response()
        await msg.edit(content=tunables('PLAYTIME_CONTENT_MSG'), embed=modified_playtime_embed(
            self.user, self.game, self.result[self.offset:self.offset+self.limit],
            self.sort, self.limit, self.updates,
            offset=self.offset, scope=self.scope,
            total=self.total, avg=self.avg),
            view=self)


    @discord.ui.button(style=discord.ButtonStyle.gray, emoji=tunables('GENERIC_REFRESH_BUTTON'), custom_id="refresh")
    async def refresh_callback(self, interaction: discord.Interaction, button = discord.Button):
        await interaction.response.edit_message(embed=None, view=None, content=f"Refreshing result. This may take a few seconds... {tunables('LOADING_EMOJI')}")
        orig_msg = await interaction.original_response()
        try:
            self.result = ptv.db_executor(self.query)
            self.offset = 0
            self.total = total_playtime_result(self.result)
            self.avg = avg_playtime_result(self.result)
            self.updates = len(self.result)
            self.button_presence()
            await orig_msg.edit(content=None, embed=modified_playtime_embed(
                self.user, self.game, self.result[self.offset:self.offset+self.limit],
                self.sort, self.limit, self.updates,
                offset=self.offset, scope=self.scope,
                total=self.total, avg=self.avg),
                view=self)
        except: await orig_msg.edit(content=":exclamation: An error occured while refreshing this result.")
    
    # Only the user that ran the command to press buttons
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.author