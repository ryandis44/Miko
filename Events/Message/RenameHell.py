'''
Respond with a simple help message whenever Miko is mentioned
'''



import discord

from Database.MikoCore import MikoCore
from misc.misc import generate_nickname

async def rename_hell(mc: MikoCore) -> None:
    if mc.profile.feature_enabled('RENAME_HELL') != 1: return
    if await mc.guild.guild_messages % 20 == 0:
        user_ids = await mc.guild.rename_hell_members
        if user_ids != [] and user_ids is not None:
            await mc.message.message.add_reaction('<:nametag:1011514395630764032>')
            for user_id in user_ids:
                user = mc.user.user.guild.get_member(int(user_id))
                try: await user.edit(nick=generate_nickname(mc.message.message))
                except discord.Forbidden as e:
                    await mc.message.message.channel.send(f"Unable to rename {user.mention}, removing them from the renameany list: `{e}`")
                    await mc.guild.remove_user_from_rename_hell(user_id=user_id)
                except Exception: pass