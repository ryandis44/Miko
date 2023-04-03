import discord
from Database.GuildObjects import MikoMember


class HandlePresence:
    
    def __init__(self, u: MikoMember, b: discord.Member, a: discord.Member) -> None:
        self.u = u
        self.b = b # Before presence update
        self.a = a # After presence update
    
    async def ainit(self) -> None:
        pass