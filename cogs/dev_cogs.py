import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from Database.GuildObjects import MikoMember
from tunables import *
import os
from dotenv import load_dotenv
load_dotenv()

db = AsyncDatabase("app_commands.py")


class dev_cog(commands.Cog):
    def __init__(self, client):
        self.client: discord.Client = client

    group = app_commands.Group(name="dev", description="Miko dev commands")
    @commands.Cog.listener()
    async def on_ready(self):
        self.tree = app_commands.CommandTree(self.client)

    @group.command(name="tunables", description=f"{os.getenv('APP_CMD_PREFIX')}None")
    @app_commands.guild_only
    async def set_level_roles(self, interaction: discord.Interaction):
        await TunablesView(original_interaction=interaction).ainit()

    @group.command(name="set_level_roles", description=f"{os.getenv('APP_CMD_PREFIX')}Give all members their leveling role")
    @app_commands.guild_only
    async def set_level_roles(self, interaction: discord.Interaction):

        u = MikoMember(user=interaction.user, client=interaction.client)
        msg = await interaction.original_response()

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



    @group.command(name="tabulate_levels", description=f"{os.getenv('APP_CMD_PREFIX')}Determine all members level and XP")
    @app_commands.guild_only
    async def tabulate_levels(self, interaction: discord.Interaction):
        msg = await interaction.original_response()

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


    @group.command(name="calculate_member_numbers", description=f"{os.getenv('APP_CMD_PREFIX')}Reset and calculate all unique member numbers")
    @app_commands.guild_only
    async def calculate_member_numbers(self, interaction: discord.Interaction):

        u = MikoMember(user=interaction.user, client=interaction.client)
        msg = await interaction.original_response()

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
    




    async def interaction_check(self, interaction: discord.Interaction):
        u = MikoMember(user=interaction.user, client=interaction.client)
        await u.ainit()
        if await u.bot_permission_level >= 5:
            await interaction.response.send_message("Executing dev command...", ephemeral=True)
            await u.increment_statistic('DEV_CMDS_USED')
            return True
        
        await interaction.response.send_message(tunables('NO_PERM'), ephemeral=True)
        return False



async def setup(client: commands.Bot):
    await client.add_cog(dev_cog(client))



class TunablesView(discord.ui.View):
    def __init__(self, original_interaction: discord.Interaction) -> None:
        super().__init__(timeout=tunables('GLOBAL_VIEW_TIMEOUT'))
        self.original_interaction = original_interaction
        self.query = None
        self.offset = 0
        self.val = all_tunable_keys()
        self.val_len = len(self.val)

    async def ainit(self) -> None:
        self.u = MikoMember(user=self.original_interaction.user, client=self.original_interaction.client)
        self.message = await self.original_interaction.original_response()
        await self.main_response()

    async def on_timeout(self) -> None:
        try: await self.message.delete()
        except: pass
    
    async def main_response(self) -> None:
        temp = []
        temp.append(
            "Search: "
            f"`{'(all)' if self.query is None else self.query}`"
            "\n\n"
        )
        
        for i, key in enumerate(self.val[self.offset:self.offset+tunables('SETTINGS_UI_MAX_SETTINGS_LISTABLE')]):
            temp.append(
                f"`{i+1+self.offset}.` `{key}`\n"
                "```\n"
                f"{tunables(key)}"
                "\n```\n"
            )
        
        embed = discord.Embed(color=GLOBAL_EMBED_COLOR, description=''.join(temp))
        embed.set_author(icon_url=self.u.client.user.avatar, name=f"{self.u.client.user.name} Tunables Editor")
        
        self.clear_items()
        self.add_item(Dropdown(tun=self.val[self.offset:self.offset+tunables('SETTINGS_UI_MAX_SETTINGS_LISTABLE')]))
        # self.add_item(SearchButton())
        if self.val_len > tunables('SETTINGS_UI_MAX_SETTINGS_LISTABLE'):
            self.add_item(PrevButton(disabled=not self.offset > 0))
            self.add_item(NextButton(
                disabled=not (self.val_len > self.offset + tunables('SETTINGS_UI_MAX_SETTINGS_LISTABLE') and \
                    self.val_len > tunables('SETTINGS_UI_MAX_SETTINGS_LISTABLE'))
            ))
        
        await self.message.edit(content=None, view=self, embed=embed)


class Dropdown(discord.ui.Select):
    def __init__(self, tun: list):
        print(tun)
        self.tun = tun

        options = []
        # options.append(
        #     discord.SelectOption(
        #         label="Test",
        #         description=None,
        #         value=0,
        #         emoji=None
        #     )
        # )

        for t in tun:
            options.append(
                discord.SelectOption(
                    label=t,
                    description=None,
                    value=t,
                    emoji=None
                )
            )

        super().__init__(
            placeholder="Select a tunable",
            min_values=1,
            max_values=1,
            options=options,
            row=1,
            custom_id="select_entry",
            disabled=False
        )
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message()
        v = self.values[0]
        print(tunables(v))

# class SearchButton(discord.ui.Button):
#     def __init__(self):
#         super().__init__(
#             style=discord.ButtonStyle.gray,
#             label=None,
#             emoji="🔎",
#             custom_id="search_button",
#             row=2
#         )
    
#     async def callback(self, interaction: discord.Interaction) -> None:
#         await interaction.response.send_modal(self.SearchModal(bview=self))

#     class SearchModal(discord.ui.Modal):

#         def __init__(self, bview):
#             super().__init__(title="Search Tunables", custom_id="search_modal")
#             self.bview = bview

#         tun = discord.ui.TextInput(
#                 label="Search (LIKE ):",
#                 placeholder="BIG_EMOJIS_ENABLED",
#                 min_length=1,
#                 max_length=50
#             )
#         async def on_submit(self, interaction: discord.Interaction) -> None:
#             await interaction.response.edit_message()
#             await self.bview.view.

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