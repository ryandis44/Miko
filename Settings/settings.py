import discord
from Database.GuildObjects import MikoMember, GuildProfile
from tunables import *
db = AsyncDatabase("Settings.settings.py")

class Setting:

    def __init__(self,
        u: MikoMember,
        p: GuildProfile,
        name: str,
        desc: str,
        emoji: str,
        table: str,
        col: str,
        options: list = None
    ) -> None:

        self.u = u
        self.name = name
        self.desc = desc
        self.emoji = emoji
        self.table = table
        self.col = col
        self.modifiable = p.feature_enabled(f'{col.upper()}')
        self.modifiable = {
            'val': True if self.modifiable == 1 else False,
            'reason': \
                "- Not enabled in this guild. -"\
                    if self.modifiable == 0 else \
                        "- Temporarily disabled in all guilds. -"
        }
        
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
                    emoji="☑"
                ),
                discord.SelectOption(
                    label=f"Disable {self.name}",
                    description=f"Select to disable {self.name} {ctx}",
                    value="FALSE",
                    emoji="❌"
                )
            ]
    
    
    def __str__(self): return f"{self.name} Settings Object"


    async def value(self, channel_id=None):
        match self.table:
            case 'CHANNELS': scope = f"channel_id='{channel_id}'"
            case 'SERVERS': scope = f"server_id='{self.u.guild.id}'"
            case _: scope = f"user_id='{self.u.user.id}'"
            
        val = await db.execute(
            f"SELECT {self.col} FROM {self.table} WHERE "
            f"{scope} LIMIT 1"
        )
        if val == "FALSE": return False
        elif val == "TRUE": return True
        return val
    
    async def value_str(self, channel_id=None):
        val = await self.value(channel_id=channel_id)
        if type(val) == bool:
            if val: state = "+ ENABLED +"
            else: state = "- DISABLED -"
        else:
            val = val.upper()
            if val == "DISABLED": state = "- DISABLED -"
            else: state = f"+ {val} +"
        
        if not self.modifiable['val']: state = "- DISABLED -"
        
        return (
            "```diff\n"
            f"{state}\n"
            f"{'' if self.modifiable['val'] else self.modifiable['reason']}"
            "```"
        )
    
    

    async def set_state(self, state=None, channel_id=None) -> str:
        val = await self.value(channel_id=channel_id)
        
        match self.table:
            case 'CHANNELS': scope = f"channel_id='{channel_id}'"
            case 'SERVERS': scope = f"server_id='{self.u.guild.id}'"
            case _: scope = f"user_id='{self.u.user.id}'"
        
        # If state is None, then val must be bool. Set to opposite.
        if state is None: state = 'TRUE' if val else 'FALSE'
        
        await db.execute(
            f"UPDATE {self.table} SET {self.col}='{state}' WHERE "
            f"{scope}"
        )
        return state