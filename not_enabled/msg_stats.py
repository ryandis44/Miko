import json
import discord
from discord.ext import commands
from discord.ui import View
from Database.database import top_users_embed_server
from utils.dropdown import Select

class MsgStats(commands.Cog):
  def __init__(self, client):
    self.client = client

    #@commands.command(name='stop', aliases=['st'])
    #async def top(self, ctx):
    #    await ctx.send(embed=top_users_embed_server(ctx.guild))


async def setup(client):
  await client.add_cog(MsgStats(client))
  



    #@commands.command(name='stop', aliases=['st'])
    #async def top(self, ctx, button: discord.ui.Button, interaction: discord.Interaction):
    #
    #
    #    await ctx.send(type=discord.InteractionType.ChannelMessageWithSource, embed=top_users_embed_server(ctx.guild))  