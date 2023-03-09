import discord

class Select(discord.ui.Select):
  def __init__(self, data):
    options = []
    for i in range(0, len(data)):
      if data[i]['title']['english'] == None:
        options.append(discord.SelectOption(label=f"{data[i]['title']['romaji']}"))
      else:
        options.append(discord.SelectOption(label=f"{data[i]['title']['english']}"))

    super().__init__(placeholder="Select an option", options=options)