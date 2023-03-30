import discord
from tunables import *
db = AsyncDatabase("Settings.settings.py")

class Setting:

    def __init__(self,
        name: str,
        desc: str,
        emoji: str,
        table: str,
        col: str,
        options: list = None
    ) -> None:

        self.name = name
        self.desc = desc
        self.emoji = emoji
        self.table = table
        self.col = col
        self.modifiable = tunables(f'SETTING_MODIFYABLE_{col.upper()}')
        
        if options is not None: self.options = options
        else:
            match self.table:
                case 'CHANNELS': ctx = "in this channel."
                case 'SERVERS': ctx = "in this guild."
                case _: ctx = "for yourself."
            
            self.options = [
                discord.SelectOption(
                    label=f"Enable {self.name}",
                    description=f"Select to enable {self.name} {ctx}",
                    value="TRUE",
                    emoji="✔"
                ),
                discord.SelectOption(
                    label=f"Disable {self.name}",
                    description=f"Select to disable {self.name} {ctx}",
                    value="FALSE",
                    emoji="❌"
                )
            ]
    
    
    def __str__(self): return f"{self.name} Settings Object"



    # BANDAID ### FIX ASAP
    async def value(self, user_id=None, server_id=None) -> bool:

        if user_id is not None: scope = f"user_id='{user_id}'"
        else: scope = f"server_id='{server_id}'"
        val = await db.execute(
            f"SELECT {self.col} FROM {self.table} WHERE "
            f"{scope}"
        )
        if val == "FALSE": return False
        return True
    
    async def value_str(self, user_id=None, server_id=None, invert=False):
        val = await self.value(user_id=user_id, server_id=server_id)
        if (val and not invert) or (not val and invert):
            return (
                "```diff\n"
                "+ ENABLED +\n"
                f"{'' if self.modifiable else '- Changing this setting is currently disabled. -'}"
                "```"
            )
        else: return (
                "```diff\n"
                "- DISABLED -\n"
                f"{'' if self.modifiable else '- Changing this setting is currently disabled. -'}"
                "```"
            )
    
    
    
    
    # BANDAID ### FIX ASAP
    async def toggle(self, user_id=None, server_id=None) -> bool:
        val = None
        if await self.value(user_id=user_id, server_id=server_id): val = "FALSE"
        else: val = "TRUE"

        if user_id is not None: scope = f"user_id='{user_id}'"
        else: scope = f"server_id='{server_id}'"
        await db.execute(
            f"UPDATE {self.table} SET {self.col}='{val}' WHERE "
            f"{scope}"
        )
        if val == "FALSE": return False
        return True