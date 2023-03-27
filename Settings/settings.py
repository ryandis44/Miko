import discord
from Database.database_class import AsyncDatabase
db = AsyncDatabase("Settings.settings.py")

class Setting:

    def __init__(self,
        name: str,
        desc: str,
        emoji: str,
        table: str,
        col: str,
        toggleable: bool = True
    ) -> None:

        self.name = name
        self.desc = desc
        self.emoji = emoji
        self.table = table
        self.col = col
        self.toggleable = toggleable
    
    def __str__(self): return self.name

    def value(self, user_id=None, server_id=None) -> bool:

        if user_id is not None: scope = f"user_id='{user_id}'"
        else: scope = f"server_id='{server_id}'"
        val = await db.execute(
            f"SELECT {self.col} FROM {self.table} WHERE "
            f"{scope}"
        )
        if val == "FALSE": return False
        return True
    
    def value_str(self, user_id=None, server_id=None, invert=False):
        val = self.value(user_id=user_id, server_id=server_id)
        if (val and not invert) or (not val and invert):
            return (
                "```diff\n"
                "+ ENABLED +\n"
                f"{'' if self.toggleable else '- Toggling this setting is currently disabled. -'}"
                "```"
            )
        else: return (
                "```diff\n"
                "- DISABLED -\n"
                f"{'' if self.toggleable else '- Toggling this setting is currently disabled. -'}"
                "```"
            )
    
    def toggle(self, user_id=None, server_id=None) -> bool:
        val = None
        if self.value(user_id=user_id, server_id=server_id): val = "FALSE"
        else: val = "TRUE"

        if user_id is not None: scope = f"user_id='{user_id}'"
        else: scope = f"server_id='{server_id}'"
        await db.execute(
            f"UPDATE {self.table} SET {self.col}='{val}' WHERE "
            f"{scope}"
        )
        if val == "FALSE": return False
        return True