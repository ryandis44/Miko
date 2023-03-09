from dpyConsole import Cog
from dpyConsole import console
import discord
from discord.utils import get


class ConsoleCog(Cog):
    def __init__(self, console):
        super(ConsoleCog, self).__init__()
        self.console = console

    #@console.command()
    #async def say(self, channel, *msg):
    #    usage = "Usage: <channel ID> <msg>"
    #    if not channel.isdigit():
    #        print(usage)
    #        return
    #    else:
    #        channel = console.Converter.channel_converter(975417946006515742)
    #    if len(msg) == 0:
    #        print(usage)
    #        return
    #    
    #    print(''.join(msg))
    #    await channel.send("Test")
    #    #await user.send("Hello from Console \n"
    #    #                f"This command operates in a Cog and my name is {self.console.client.user.name}")


def setup(console):
    console.add_console_cog(ConsoleCog(console))