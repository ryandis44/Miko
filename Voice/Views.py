import time
import discord
from discord.ui import View
from Voice.track_voice import avg_voicetime_result, total_voicetime_result
from tunables import *
import typing
from Database.database_class import Database
from tunables import *
from Voice.embeds import voicetime_embed, voicetime_search_embed
from Playtime.playtime import avg_playtime_result, total_playtime_result

ptv = Database("Playtime.Views.py")

class VoicetimePageSelector(View):
    
    '''
    This view works by allowing the user to advance to the next page
    if there is a next page (based off of self.updates). It will also
    let the user go to the previous page (offset) if there is one.
    
    When there is not a previos or next page, the individual buttons
    are disabled/enabled by the button_presence() function
    '''
    
    def __init__(self, client: discord.Client, user: discord.User, guild: discord.Guild, voicetime_guild: int,
                author: discord.User, page_size, updates, voicetime=0, avg_session="`None`"):
        super().__init__(timeout=120)
        self.client = client # for guild name
        self.user = user
        self.author = author
        self.page_size = page_size
        self.offset = 0
        self.updates = updates
        self.voicetime = voicetime
        self.avg = avg_session
        self.guild = guild
        self.voicetime_guild = voicetime_guild
    

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
        
        if self.updates > self.offset + self.page_size:
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
        await msg.edit(content=tunables('VOICETIME_CONTENT_MSG'), embed=await voicetime_embed(client=self.client, user=self.user, page_size=self.page_size,
                                                offset=self.offset, updates=self.updates, voicetime=self.voicetime, avg_session=self.avg,
                                                guild=self.guild, voicetime_guild=self.voicetime_guild), view=self)

    @discord.ui.button(style=discord.ButtonStyle.gray, emoji=tunables('GENERIC_PREV_BUTTON'), custom_id="back", disabled=True)
    async def back_callback(self, interaction: discord.Interaction, button = discord.Button):
        # If 8 <= 10
        if self.offset <= self.page_size: self.offset = 0 
        # If 8 > 8 - 10
        elif self.offset > self.offset - self.page_size: self.offset -= self.page_size
        else: return
        self.button_presence()
        await interaction.response.edit_message()
        msg = await interaction.original_response()
        await msg.edit(content=tunables('VOICETIME_CONTENT_MSG'), embed=await voicetime_embed(client=self.client, user=self.user, page_size=self.page_size,
                                                offset=self.offset, updates=self.updates, voicetime=self.voicetime, avg_session=self.avg,
                                                guild=self.guild, voicetime_guild=self.voicetime_guild), view=self)
    
    @discord.ui.button(style=discord.ButtonStyle.gray, emoji=tunables('GENERIC_NEXT_BUTTON'), custom_id="next")
    async def forward_callback(self, interaction: discord.Interaction, button = discord.Button):
        # if 17 > 0 + 20 == False
        if self.updates > self.offset + (self.page_size * 2): self.offset += self.page_size
        # If 17 <= 0 + 20 == True
        elif self.updates <= self.offset + (self.page_size * 2): self.offset = self.updates - self.page_size
        else: return
        self.button_presence()
        await interaction.response.edit_message()
        msg = await interaction.original_response()
        await msg.edit(content=tunables('VOICETIME_CONTENT_MSG'), embed=await voicetime_embed(client=self.client, user=self.user, page_size=self.page_size,
                                                offset=self.offset, updates=self.updates, voicetime=self.voicetime, avg_session=self.avg,
                                                guild=self.guild, voicetime_guild=self.voicetime_guild), view=self)
    
    @discord.ui.button(style=discord.ButtonStyle.gray, emoji=tunables('GENERIC_LAST_BUTTON'), custom_id="end")
    async def end_callback(self, interaction: discord.Interaction, button = discord.Button):
        self.offset = self.updates - self.page_size
        self.button_presence()
        await interaction.response.edit_message()
        msg = await interaction.original_response()
        await msg.edit(content=tunables('VOICETIME_CONTENT_MSG'), embed=await voicetime_embed(client=self.client, user=self.user, page_size=self.page_size,
                                                offset=self.offset, updates=self.updates, voicetime=self.voicetime, avg_session=self.avg,
                                                guild=self.guild, voicetime_guild=self.voicetime_guild), view=self)
    
    # Only the user that ran the command to press buttons
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.author















class VoicetimeSearchPageSelector(View):
    '''
    This view works by allowing the user to advance to the next page
    if there is a next page (based off of self.updates). It will also
    let the user go to the previous page (offset) if there is one.
    
    When there is not a previos or next page, the individual buttons
    are disabled/enabled by the button_presence() function
    '''
    
    def __init__(self, author, user, client, guild, sort, page_size, query, results, vtquery, search_results, user_scope, total, avg):
        super().__init__(timeout=120)
        self.author: discord.Member = author
        self.user: discord.User = user
        self.client: discord.Client = client
        self.guild: discord.Guild = guild
        self.search_results = search_results
        self.page_size = page_size
        self.results = results
        self.sort = sort
        self.user_scope = user_scope
        self.vtquery = vtquery
        self.offset = 0
        self.query = query
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
        
        if self.results > self.offset + self.page_size:
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
        await msg.edit(content=tunables('VOICETIME_CONTENT_MSG'), embed=await voicetime_search_embed(
            user=self.user,
            client=self.client,
            guild=self.guild,
            search_results=self.search_results[self.offset:self.offset+self.page_size],
            sort=self.sort,
            page_size=self.page_size,
            results=self.results,
            user_scope=self.user_scope,
            vtquery=self.vtquery,
            total=self.total,
            avg=self.avg,
            offset=self.offset
            ), view=self)

    @discord.ui.button(style=discord.ButtonStyle.gray, emoji=tunables('GENERIC_PREV_BUTTON'), custom_id="back", disabled=True)
    async def back_callback(self, interaction: discord.Interaction, button = discord.Button):
        # If 8 <= 10
        if self.offset <= self.page_size: self.offset = 0 
        # If 8 > 8 - 10
        elif self.offset > self.offset - self.page_size: self.offset -= self.page_size
        else: return
        self.button_presence()
        await interaction.response.edit_message()
        msg = await interaction.original_response()
        await msg.edit(content=tunables('VOICETIME_CONTENT_MSG'), embed=await voicetime_search_embed(
            user=self.user,
            client=self.client,
            guild=self.guild,
            search_results=self.search_results[self.offset:self.offset+self.page_size],
            sort=self.sort,
            page_size=self.page_size,
            results=self.results,
            user_scope=self.user_scope,
            vtquery=self.vtquery,
            total=self.total,
            avg=self.avg,
            offset=self.offset
            ), view=self)
    
    @discord.ui.button(style=discord.ButtonStyle.gray, emoji=tunables('GENERIC_NEXT_BUTTON'), custom_id="next")
    async def forward_callback(self, interaction: discord.Interaction, button = discord.Button):
        # if 17 > 0 + 20 == False
        if self.results > self.offset + (self.page_size * 2): self.offset += self.page_size
        # If 17 <= 0 + 20 == True
        elif self.results <= self.offset + (self.page_size * 2): self.offset = self.results - self.page_size
        else: return
        self.button_presence()
        await interaction.response.edit_message()
        msg = await interaction.original_response()
        await msg.edit(content=tunables('VOICETIME_CONTENT_MSG'), embed=await voicetime_search_embed(
            user=self.user,
            client=self.client,
            guild=self.guild,
            search_results=self.search_results[self.offset:self.offset+self.page_size],
            sort=self.sort,
            page_size=self.page_size,
            results=self.results,
            user_scope=self.user_scope,
            vtquery=self.vtquery,
            total=self.total,
            avg=self.avg,
            offset=self.offset
            ), view=self)

    
    @discord.ui.button(style=discord.ButtonStyle.gray, emoji=tunables('GENERIC_LAST_BUTTON'), custom_id="end")
    async def end_callback(self, interaction: discord.Interaction, button = discord.Button):
        self.offset = self.results - self.page_size
        self.button_presence()
        await interaction.response.edit_message()
        msg = await interaction.original_response()
        await msg.edit(content=tunables('VOICETIME_CONTENT_MSG'), embed=await voicetime_search_embed(
            user=self.user,
            client=self.client,
            guild=self.guild,
            search_results=self.search_results[self.offset:self.offset+self.page_size],
            sort=self.sort,
            page_size=self.page_size,
            results=self.results,
            user_scope=self.user_scope,
            vtquery=self.vtquery,
            total=self.total,
            avg=self.avg,
            offset=self.offset
            ), view=self)


    @discord.ui.button(style=discord.ButtonStyle.gray, emoji=tunables('GENERIC_REFRESH_BUTTON'), custom_id="refresh")
    async def refresh_callback(self, interaction: discord.Interaction, button = discord.Button):
        await interaction.response.edit_message(embed=None, view=None, content=f"Refreshing result. This may take a few seconds... {tunables('LOADING_EMOJI')}")
        msg = await interaction.original_response()
        try:
            self.search_results = ptv.db_executor(self.query)
            self.offset = 0
            self.total = total_voicetime_result(self.search_results)
            self.avg = avg_voicetime_result(self.search_results)
            self.results = len(self.search_results)
            self.button_presence()
            await msg.edit(content=tunables('VOICETIME_CONTENT_MSG'), embed=await voicetime_search_embed(
                user=self.user,
                client=self.client,
                guild=self.guild,
                search_results=self.search_results[self.offset:self.offset+self.page_size],
                sort=self.sort,
                page_size=self.page_size,
                results=self.results,
                user_scope=self.user_scope,
                vtquery=self.vtquery,
                total=self.total,
                avg=self.avg
                ), view=self)
        except: await msg.edit(content=":exclamation: An error occured while refreshing this result.")
    
    # Only the user that ran the command to press buttons
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.author