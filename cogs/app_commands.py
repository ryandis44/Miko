import asyncio
from curses.ascii import isdigit
import random
import discord
from discord.ext import commands
from discord import app_commands
import typing
from Database.GuildObjects import MikoMember
from tunables import *
import os
from dotenv import load_dotenv
load_dotenv()

db = AsyncDatabase("app_commands.py")
        

class Slash(commands.Cog):
    def __init__(self, client):
        self.client: discord.Client = client
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.tree = app_commands.CommandTree(self.client)

    # Sync command cannot be a slash command because you have to sync slash commands, so we cannot sync
    # the sync command if we have not synced slash commands. Sync sync sync
    @commands.command(name='sync', aliases=['sc'])
    @commands.guild_only()
    async def sync(
      self, ctx: commands.Context, guilds: commands.Greedy[discord.Object], spec: typing.Optional[typing.Literal["~", "*", "^", "G"]] = None) -> None:
        u = MikoMember(user=ctx.author, client=self.client)
        if await u.bot_permission_level <= 4: return
        if spec is not None: await ctx.channel.send("Attempting to sync commands...")
        if not guilds:
            if spec == "~":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            elif spec == "G":
                synced = await ctx.bot.tree.sync()
            else:
                await ctx.channel.send(
                    "Please provide a modifier: `sc <modifier>`\n"+
                    "`~` Locally syncs private guild commands to current guild (if they are listed on this server)\n"+
                    "`*` Syncs global commands to current guild\n"+
                    "`^` Clears all locally synced commands from current guild\n"+
                    "`G` Globally syncs all non-private commands to all guilds\n"
                )
                return

            await ctx.send(
                f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
            )
            return

        ret = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                ret += 1

        await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")


    @app_commands.command(name="roleaddall", description=f"{os.getenv('APP_CMD_PREFIX')}Add a role to everyone in this guild")
    @app_commands.guild_only
    async def roleaddall(self, interaction: discord.Interaction, role: discord.Role):

        u = MikoMember(user=interaction.user, client=interaction.client)
        
        if not u.user.guild_permissions.manage_roles:
            await interaction.response.send_message(tunables('NO_PERM'))
            return
        
        temp = []
        temp.append(f"Adding {role.mention} to all guild members... {tunables('LOADING_EMOJI')}")
        await interaction.response.send_message(''.join(temp))
        temp.append("\n[")
        temp.append("?")
        temp.append(f"/{interaction.guild.member_count}]")
        msg = await interaction.original_response()

        for i, member in enumerate(interaction.guild.members):
            await member.add_roles(role)
            if i % 10 == 0:
                temp[2] = f"{i+1}"
                await msg.edit(content=''.join(temp))
        
        temp[2] = f"{interaction.guild.member_count}"
        temp.append(" — Complete.")
        temp[0] = f"Added {role.mention} to all guild members."
        await msg.edit(content=''.join(temp))
        


    @app_commands.command(name="renameall", description=f"{os.getenv('APP_CMD_PREFIX')}Rename every member of this guild")
    @app_commands.guild_only
    @app_commands.describe(
        name='Name to set everyone to (leave blank to remove all nicknames and restore to previous state)'
    )
    async def rna(self, interaction: discord.Interaction,
                  name: typing.Optional[str] = None):
        
        u = MikoMember(user=interaction.user, client=interaction.client)
        if await u.bot_permission_level <= 3 and interaction.guild.owner.id != interaction.user.id:
            await interaction.response.send_message(tunables('NO_PERM'))
            return
        
        members = interaction.guild.members

        temp = []
        temp.append("[0/0]\n\n")

        if name is None:
            temp.append("Restoring all guild member nicknames...")
            await interaction.response.send_message(''.join(temp))
            msg = await interaction.original_response()
            for i, member in enumerate(members):
                temp[0] = f"[{i+1}/{len(members)}]\n\n"
                await asyncio.sleep(1)

                # Restore and delete nick cache
                sel_cmd = f"SELECT name FROM NICKNAME_CACHE WHERE user_id='{member.id}' AND server_id='{interaction.guild.id}' ORDER BY user_id DESC LIMIT 1"
                rst_name = await db.execute(sel_cmd)
                del_cmd = f"DELETE FROM NICKNAME_CACHE WHERE user_id='{member.id}' AND server_id='{interaction.guild.id}'"
                await db.execute(del_cmd)
                if rst_name == []: rst_name = None

                try: await member.edit(nick=rst_name)
                except discord.Forbidden as e:
                    temp.append("\n")
                    temp.append(f"Unable to remove nickname for {member.mention}: `{e}`")
                await msg.edit(content=''.join(temp))
            temp.append("\n\n**Complete!** Removed as many nicknames as I could.")
            await msg.edit(content=''.join(temp))
            return

        temp.append(f"Renaming all guild members to `{name}`")

        await interaction.response.send_message(content=''.join(temp))
        msg = await interaction.original_response()

        for i, member in enumerate(members):
            temp[0] = f"[{i+1}/{len(members)}]\n\n"

            # Remember what their nick was before renameall
            if member.nick is not None and member.nick != name:
                ins_cmd = (
                    "INSERT INTO NICKNAME_CACHE (server_id,user_id,name) VALUES "+
                    f"('{interaction.guild.id}', '{member.id}', '{member.nick}')"
                )
                await db.execute(ins_cmd)

            await asyncio.sleep(1)
            try: await member.edit(nick=name)
            except discord.Forbidden as e:
                temp.append("\n")
                temp.append(f"Unable to rename {member.mention}: `{e}`")
            await msg.edit(content=''.join(temp))
        
        temp.append("\n\n**Complete!** Renamed all members that I could.")
        await msg.edit(content=''.join(temp))


    @app_commands.command(name="renameallrandom", description=f"{os.getenv('APP_CMD_PREFIX')}Rename every member of this guild to the name of another member")
    @app_commands.guild_only
    @app_commands.describe(rename="True will set everyone to random name. False will undo.")
    async def rna(self, interaction: discord.Interaction, rename: bool):
        u = MikoMember(user=interaction.user, client=interaction.client)
        if not await u.manage_guild:
            await interaction.response.send_message(content=f"{tunables('NO_PERM')}: Need `Manage Guild` permission.")
            return
        
        if rename: temp = ["Renaming all members to the name of another member..."]
        else: temp = ["Restoring all nicknames..."]
        await interaction.response.send_message(content=''.join(temp))
        msg = await interaction.original_response()
        
        members = list(interaction.guild.members)
        names = list(interaction.guild.members)

        temp.append("\n\n[")
        temp.append("0")
        temp.append(f"/{len(members)}] Running...")
        try:
            if rename:
                for i, member in enumerate(members):
                    while True:
                        n = random.randint(0, len(names)-1)
                        n = names.pop(n).name
                        if n != member.name: break
                    
                    if i % 10 == 0:
                        temp[2] = f"{i+1}"
                        await msg.edit(content=''.join(temp))
                    
                    if member.nick is not None:
                        await db.execute(
                            "INSERT INTO NICKNAME_CACHE (server_id,user_id,name) VALUES "
                            f"('{interaction.guild.id}', '{member.id}', '{member.nick}')"
                        )
                    try: await member.edit(nick=n)
                    except:
                        temp.append(f"\n\nRename yourself to: {n}")
                        await msg.edit(content=''.join(temp))
                    await asyncio.sleep(1)
            else:
                names = await db.execute(
                    "SELECT user_id, name FROM NICKNAME_CACHE WHERE "
                    f"server_id='{interaction.guild.id}'"
                )
                
                for i, member in enumerate(members):
                    if i % 10 == 0:
                        temp[2] = f"{i+1}"
                        await msg.edit(content=''.join(temp))
                    
                    n = await db.execute(
                        "SELECT name FROM NICKNAME_CACHE WHERE "
                        f"server_id='{interaction.guild.id}' AND "
                        f"user_id='{member.id}' LIMIT 1"
                    )
                    if n is not None and n != []:
                        await db.execute(
                            "DELETE FROM NICKNAME_CACHE WHERE "
                            f"server_id='{interaction.guild.id}' AND "
                            f"user_id='{member.id}'"
                        )
                    try: await member.edit(nick=n if n is not None and n != [] else None)
                    except: pass
                    await asyncio.sleep(1)

            temp[2] = f"{len(members)}"
            temp.append("\n\nComplete!")
        except Exception as e: print(e)

        await msg.edit(content=''.join(temp))


    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        u = MikoMember(user=interaction.user, client=interaction.client)
        await u.ainit()
        if (await u.profile).cmd_enabled('MISC_CMDS') != 1:
            await interaction.response.send_message(content=tunables('GENERIC_BOT_DISABLED_MESSAGE'), ephemeral=True)
            return False
        return True



async def setup(client: commands.Bot):
    await client.add_cog(Slash(client))