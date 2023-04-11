import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from Database.GuildObjects import MikoMember, MikoGuild
from tunables import *
import os
from dotenv import load_dotenv
load_dotenv()

db = AsyncDatabase("app_commands.py")


class dev_cog(commands.Cog):
    def __init__(self, client):
        self.client: discord.Client = client

    @commands.Cog.listener()
    async def on_ready(self):
        self.tree = app_commands.CommandTree(self.client)

    @app_commands.command(name="dev", description=f"{os.getenv('APP_CMD_PREFIX')}Development commands")
    @app_commands.guilds(discord.Object(id=890638458211680256))
    @app_commands.guild_only
    async def dev(self, interaction: discord.Interaction, mode: str=None, params: str=None):
        msg = await interaction.original_response()
        
        fail = (
            "Possible options: `set_level_roles`, `tunables`, `tabulate_levels`, "
            "`calculate_member_numbers`, `re_add_members <guild id>`"
        )
        if mode is None:
            await msg.edit(content=fail)
            return

        
        match mode.lower():
            
            case "tunables": await TunablesView(original_interaction=interaction).ainit()
            
            #####################################################################################
            
            case "set_level_roles":
                temp = []
                members = interaction.guild.members
                temp.append(f"Assigning leveling roles to all users... {tunables('LOADING_EMOJI')}")
                await msg.edit(content=''.join(temp))

                leveling_roles = [
                    interaction.guild.get_role(tunables('RANK_ID_LEVEL_01')),
                    interaction.guild.get_role(tunables('RANK_ID_LEVEL_05')),
                    interaction.guild.get_role(tunables('RANK_ID_LEVEL_10'))
                ]

                temp.append("\n[")
                temp.append("?")
                temp.append(f"/{interaction.guild.member_count}]")
                for i, member in enumerate(members):
                    m = MikoMember(user=member, client=interaction.client)
                    if member.bot: continue
                    await member.remove_roles(*leveling_roles)
                    await member.add_roles(await m.leveling.get_role())
                    if i % 10 == 0:
                        temp[2] = f"{i+1}"
                        await msg.edit(content=''.join(temp))

                temp[2] = f"{interaction.guild.member_count}"
                temp[0] = "Assigning leveling roles to all users..."
                temp.append("\n\n**Complete!** Leveling roles have been assigned to all users")
                await msg.edit(content=''.join(temp))
            
            #####################################################################################
            
            case "tabulate_levels":
                temp = []
                temp.append(f"Compiling user data and determining all XP levels and ranks in this guild... {tunables('LOADING_EMOJI')}")
                await msg.edit(content=''.join(temp))

                sel_cmd = (
                    "SELECT user_id FROM USERS WHERE "
                    f"server_id='{interaction.guild.id}'"
                )
                msg_totals = await db.execute(sel_cmd)

                temp.append("\n[")
                temp.append("?")
                temp.append(f"/{interaction.guild.member_count}]")
                for i, user in enumerate(msg_totals):
                    user_obj = self.client.get_user(int(msg_totals if type(msg_totals) is str else user[0]))
                    if user_obj is None: continue
                    u = MikoMember(user=user_obj, client=interaction.client, guild_id=interaction.guild.id)
                    lc = u.leveling

                    times_to_give_xp = int(await lc.msgs / tunables('THRESHOLD_MESSAGES_FOR_XP'))
                    xp = times_to_give_xp * tunables('XP_GAINED_FROM_MESSAGES')
                    await lc.add_xp_msg(xp=xp, manual=True)

                    times_to_give_xp = int(await u.user_voicetime / tunables('THRESHOLD_VOICETIME_FOR_XP'))
                    xp = times_to_give_xp * tunables('XP_GAINED_FROM_VOICETIME')
                    await lc.add_xp_voice(xp=xp, manual=True)
                    if type(msg_totals) == int: break
                    if i % 10 == 0:
                        temp[3] = f"{i+1}"
                        await msg.edit(content=''.join(temp))


                temp[2] = f"{interaction.guild.member_count}"
                temp[0] = "Assigning leveling roles to all users..."
                temp.append("\n\n**Complete!** Levels and xp has been added")
                await msg.edit(content=''.join(temp))
                
            #####################################################################################
            
            case "calculate_member_numbers":
                temp = []
                members = interaction.guild.members
                temp.append(f"Resetting and recalculating all unique member numbers... {tunables('LOADING_EMOJI')}")
                await msg.edit(content=''.join(temp))


                temp.append("\nEnsuring all members are in database... [")
                temp.append("?")
                temp.append(f"/{interaction.guild.member_count}]")
                for i, member in enumerate(members):
                    m = MikoMember(user=member, client=interaction.client)
                    if i % 10 == 0:
                        temp[2] = f"{i+1}"
                        await msg.edit(content=''.join(temp))

                temp[2] = f"{interaction.guild.member_count}"



                db_members = await db.execute(
                    "SELECT user_id FROM USERS WHERE "
                    f"server_id='{interaction.guild.id}' "
                    "ORDER BY original_join_time ASC"
                )

                temp.append("\nRecalculating unique member numbers... [")
                temp.append("?")
                temp.append(f"/{interaction.guild.member_count}]")
                for i, db_member in enumerate(db_members):
                    
                    await db.execute(
                        f"UPDATE USERS SET unique_number='{i+1}' WHERE "
                        f"user_id='{db_member[0]}' AND server_id='{interaction.guild.id}'"
                    )
                    if i % 10 == 0:
                        temp[5] = f"{i+1}"
                        await msg.edit(content=''.join(temp))

                temp[5] = f"{interaction.guild.member_count}"
                temp[0] = "Reset and recalculated all unique member numbers."
                temp.append("\n\n**Complete!**")
                await msg.edit(content=''.join(temp))
                
            #####################################################################################
            
            case 're_add_members':
                try:
                    g = MikoGuild(guild_id=params, client=self.client, guild=None)
                    await msg.edit(content=f"Adding all members of `{g.guild}` to database and calculating member numbers... {tunables('LOADING_EMOJI')}")
                    await g.add_all_members()
                    await msg.edit(
                        content=(
                            f"**Success!**\nAdded all members of `{g.guild}` "
                            "to the database and recalculated all member "
                            "numbers."
                        )
                    )
                except Exception as e: await msg.edit(content=f"Error: {e}")
            
            case _: await msg.edit(content=fail)
    
    async def interaction_check(self, interaction: discord.Interaction):
        u = MikoMember(user=interaction.user, client=interaction.client)
        await u.ainit()
        if await u.bot_permission_level >= 5 and interaction.guild.id == 890638458211680256:
            await interaction.response.send_message(content=tunables('LOADING_EMOJI'), ephemeral=True)
            await u.increment_statistic('DEV_CMDS_USED')
            return True
        
        await interaction.response.send_message(tunables('NO_PERM'), ephemeral=True)
        return False



async def setup(client: commands.Bot):
    await client.add_cog(dev_cog(client))











# Tunables editor main class
class TunablesView(discord.ui.View):
    def __init__(self, original_interaction: discord.Interaction) -> None:
        super().__init__(timeout=tunables('GLOBAL_VIEW_TIMEOUT'))
        self.original_interaction = original_interaction
        self.offset = 0

    async def ainit(self) -> None:
        self.u = MikoMember(user=self.original_interaction.user, client=self.original_interaction.client)
        self.message = await self.original_interaction.original_response()
        await self.main_response(refresh=True)
    
    async def __db(self, query=None) -> None:
        if query is None: w = ""
        else: w = f"WHERE variable LIKE '%{query}%' "
        self.val = await db.execute(
            "SELECT * FROM TUNABLES "
            f"{w}"
            "ORDER BY variable ASC"
        )
        self.val_len = len(self.val)

    async def on_timeout(self) -> None:
        try: await self.message.delete()
        except: pass
    
    async def main_response(self, query=None, refresh=False) -> None:
        if refresh or query is not None:
            self.offset = 0
            await self.__db(query=query)
        temp = []
        temp.append(
            "Search: "
            f"`{'(all)' if query is None else query}`"
            "\n"
            f"Total: `{self.val_len:,}`"
            "\n\n"
        )
        
        if self.val != []:
            for i, key in enumerate(self.val[self.offset:self.offset+tunables('SETTINGS_UI_MAX_SETTINGS_LISTABLE')]):
                temp.append(
                    f"`{i+1+self.offset}.` `{key[0]}`\n"
                    "```\n"
                    f"{key[1]}"
                    "\n```\n"
                )
        else: temp.append("No results.")
        
        embed = discord.Embed(color=GLOBAL_EMBED_COLOR, description=''.join(temp))
        embed.set_author(icon_url=self.u.client.user.avatar, name=f"{self.u.client.user.name} Tunables Editor")
        
        self.clear_items()
        if self.val_len > 0: self.add_item(Dropdown(tun=self.val[self.offset:self.offset+tunables('SETTINGS_UI_MAX_SETTINGS_LISTABLE')], offset=self.offset))
        self.add_item(NewTunable())
        self.add_item(SearchButton())
        self.add_item(HomeButton())
        if self.val_len > tunables('SETTINGS_UI_MAX_SETTINGS_LISTABLE'):
            self.add_item(PrevButton(disabled=not self.offset > 0))
            self.add_item(NextButton(
                disabled=not (self.val_len > self.offset + tunables('SETTINGS_UI_MAX_SETTINGS_LISTABLE') and \
                    self.val_len > tunables('SETTINGS_UI_MAX_SETTINGS_LISTABLE'))
            ))
        
        await self.message.edit(content=None, view=self, embed=embed)

# Select menu
class Dropdown(discord.ui.Select):
    def __init__(self, tun: list, offset: int):
        self.tun = tun

        options = []

        for i, t in enumerate(tun):
            options.append(
                discord.SelectOption(
                    label=f"{i+1+offset}. {t[0]}",
                    description=None,
                    value=i,
                    emoji=None
                )
            )

        super().__init__(
            placeholder="Select a tunable",
            min_values=0,
            max_values=1,
            options=options,
            row=1,
            custom_id="select_entry",
            disabled=False
        )
    
    async def callback(self, interaction: discord.Interaction):
        if len(self.values) < 1:
            await interaction.response.edit_message()
            return
        v = int(self.values[0])
        m = TunableModal(prev=self)
        m.keyy.default = self.tun[v][0]
        m.vall.default = self.tun[v][1]
        await interaction.response.send_modal(m)

# New tunable button
class NewTunable(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(
            style=discord.ButtonStyle.green,
            label="New",
            emoji=None,
            custom_id="new_button",
            row=2
        )
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(TunableModal(prev=self))

# For modifying old and creating new tunables    
class TunableModal(discord.ui.Modal):
    def __init__(self, prev: Dropdown):
        super().__init__(title="Tunable Entry", custom_id="entry_modal")
        self.prev = prev

    keyy = discord.ui.TextInput(
            label="Key",
            placeholder="COMMAND_DISABLED_TUNABLES",
            min_length=0,
            max_length=100,
            default=None,
            required=False
        )
    
    vall = discord.ui.TextInput(
            label="Value",
            placeholder="TRUE",
            min_length=0,
            max_length=4000,
            default=None,
            required=False,
            style=discord.TextStyle.paragraph
        )
    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            if self.vall.value.lower() == "true": val = "TRUE"
            elif self.vall.value.lower() == "false": val = "FALSE"
            else: val = self.vall.value
        except: val = None
        if self.keyy.value == self.keyy.default:
            await db.execute(
                f"UPDATE TUNABLES SET value='{val}' "
                f"WHERE variable='{self.keyy.value}'"
            )
            await tunables_refresh()
            await interaction.response.edit_message()
            await self.prev.view.main_response(query=self.keyy.value)
            return
        elif self.keyy.default is None:
            await db.execute(
                "INSERT INTO TUNABLES (variable,value) VALUES "
                f"('{self.keyy.value.upper()}', '{val}')"
            )
            await tunables_refresh()
            await interaction.response.edit_message()
            await self.prev.view.main_response(query=self.keyy.value)
            return
        elif (self.keyy.default is not None and self.keyy.value == ""):
            await db.execute(
                "DELETE FROM TUNABLES WHERE "
                f"variable='{self.keyy.default}' AND "
                f"value='{self.vall.default}'"
            )
            await tunables_refresh()
            await interaction.response.edit_message()
            await self.prev.view.main_response(query=self.keyy.default)
            return
    
        await interaction.response.send_message(
            content=(
                "Error: New key does not match old key:\n"
                f"NEW: `{self.keyy.value}`\n"
                f"OLD: `{self.keyy.default}`"
            ), ephemeral=True
        )

# Search tunables
class SearchButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.gray,
            label=None,
            emoji="🔎",
            custom_id="search_button",
            row=2
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(self.SearchModal(bview=self))

    class SearchModal(discord.ui.Modal):

        def __init__(self, bview):
            super().__init__(title="Search Tunables", custom_id="search_modal")
            self.bview = bview

        tun = discord.ui.TextInput(
                label="Search (LIKE ):",
                placeholder="FEATURE_ENABLED_BIG_EMOJIS",
                min_length=1,
                max_length=50
            )
        async def on_submit(self, interaction: discord.Interaction) -> None:
            await interaction.response.edit_message()
            await self.bview.view.main_response(query=self.tun.value)

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
        elif self.view.offset > self.view.offset - tunables('SETTINGS_UI_MAX_SETTINGS_LISTABLE'): \
            self.view.offset -= tunables('SETTINGS_UI_MAX_SETTINGS_LISTABLE')
        else: return
        await interaction.response.edit_message()
        await self.view.main_response()

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
        if self.view.val_len > self.view.offset + (tunables('SETTINGS_UI_MAX_SETTINGS_LISTABLE') * 2): \
            self.view.offset += tunables('SETTINGS_UI_MAX_SETTINGS_LISTABLE')
        elif self.view.val_len <= self.view.offset + (tunables('SETTINGS_UI_MAX_SETTINGS_LISTABLE') * 2): \
            self.view.offset = self.view.val_len - tunables('SETTINGS_UI_MAX_SETTINGS_LISTABLE')
        else: return
        await interaction.response.edit_message()
        await self.view.main_response()
     
# Back to "home" page   
class HomeButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(
            style=discord.ButtonStyle.gray,
            label=None,
            emoji=tunables('GENERIC_HOME_BUTTON'),
            custom_id="home_button",
            row=2
        )
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await self.view.main_response(refresh=True)