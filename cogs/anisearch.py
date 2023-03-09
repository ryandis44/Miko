import discord
from discord.ext import commands
from discord.ui import View
from utils.dropdown import Select
from utils.fetch_anime_data import fetch_anime_results
from tunables import *
from Database.GuildObjects import MikoMember

class AniSearch(commands.Cog):
  def __init__(self, client):
    self.client = client

  @commands.command(name='animesearch', aliases=['as'])
  async def animesearch(self, ctx: commands.Context, *args):
    u = MikoMember(user=ctx.author, client=self.client)
    if not u.profile.cmd_enabled('ANIME_SEARCH'): return
    u.increment_statistic('ANIME_SEARCH')
    if len(args) == 0:
      await ctx.send('Please enter a search query.')
      return
    else:
      data = fetch_anime_results(' '.join(args))
      if data == 'Error' or len(data) == 0:
          await ctx.reply('No results found. Please try again!')
      elif len(data) == 1:
        embed = display_result(data, 0)
        await ctx.reply(embed=embed)
      else:
          embed = display_options(data)
          select = Select(data)
          view = View()
          view.add_item(select)

          await ctx.reply(embed=embed, mention_author=False, view=view)

          async def wait_for_selection(interaction):
            embed_2 = display_result(data, get_index(data, select.values[0]))
            await interaction.response.edit_message(embed=embed_2)

          select.callback = wait_for_selection

def get_index(data, name):
  for index, anime in enumerate(data):
    if anime['title']['english'] == name or anime['title']['romaji'] == name:
        return index
  
  return -1

def display_options(data):
  tmp = []

  for i in range(0, len(data)):
    if data[i]['title']['english'] == None:
      desc = f"**{i+1}.** {data[i]['title']['romaji']}"
    else:
      desc = f"**{i+1}.** {data[i]['title']['english']}"
    tmp.append(desc)

  description_text = '[{}]'.format('\n'.join(tmp))

  embed = discord.Embed (
    title = 'Anime Search Results',
    color = GLOBAL_EMBED_COLOR,
    description = description_text[1:-1]
  )

  return embed

def display_result(data, i):
  embed = discord.Embed (
    title = 'Anime Search Results',
    color = GLOBAL_EMBED_COLOR
  )

  embed.set_image(url=data[i]['coverImage']['extraLarge'])

  if data[i]['title']['english'] == None:
    embed.add_field(name='Japanese Title', value=data[i]['title']['romaji'], inline=True)
  else:
    embed.add_field(name='English Title', value=data[i]['title']['english'], inline=True)
  embed.add_field(name='Japanese Title', value=data[i]['title']['romaji'], inline=True)
  embed.add_field(name='Score', value=data[i]['averageScore'], inline=True)
  embed.add_field(name='Popularity', value=f"{data[i]['popularity']} fans", inline=True)
  embed.add_field(name='Season Aired', value=f"{data[i]['season']} {data[i]['seasonYear']}", inline=True)
  embed.add_field(name='Genres', value=', '.join(data[i]['genres']), inline=True)
  embed.add_field(name='Episodes', value=data[i]['episodes'], inline=True)
  embed.add_field(name='18+?', value=data[i]['isAdult'], inline=True)
  if data[i]['nextAiringEpisode'] == None:
    embed.add_field(name='Status', value=data[i]['status'], inline=True)
  else:
    embed.add_field(name='Next Airing Episode', value=f"Episode {data[i]['nextAiringEpisode']['episode']} <t:{data[i]['nextAiringEpisode']['airingAt']}:R>", inline=True)
  
  return embed

async def setup(client):
  await client.add_cog(AniSearch(client))