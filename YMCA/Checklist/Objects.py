from datetime import date, datetime, timedelta, timezone
import time
import uuid

import discord
from Database.database_class import AsyncDatabase
from misc.misc import sanitize_name
from tunables import tunables
db = AsyncDatabase("YMCA.Checklist.Objects.py")



class ChecklistItem:

    def __init__(
        self,
        checklist,
        id: str,
        creator_id: int,
        name: str,
        description: str,
        created_at: int,
        pos: int
    ) -> None:
        
        self.checklist = checklist
        self.id = id
        self.creator_id = creator_id
        self.name = name
        self.description = description
        self.created_at = created_at
        self.pos = pos
    
    def __str__(self) -> str:
        return f"{self.name} ({self.id}) [{self.checklist.name}]"
    
    async def ainit(self) -> None:
        await self.__get_last_history()
        
    async def __get_last_history(self) -> None:
        self.actor_id: int = None
        self.completed_at: int = None
        val = await db.execute(
            "SELECT actor_id,completed_at FROM CHECKLIST_HISTORY WHERE "
            f"item_id='{self.id}' "
            "ORDER BY completed_at DESC"
        )
        if val == [] or val is None: return
        self.actor_id = val[0][0]
        self.completed_at = val[0][1]
    
    @property
    def completed(self) -> bool:
        last_reset = self.checklist.last_reset
        if type(last_reset) != int: last_reset = int(last_reset.timestamp())
        
        if self.completed_at is not None and self.completed_at >= last_reset: return True
        return False

    @property
    def bold_if_completed(self) -> str:
        if self.completed: return f"**{self.name}**"
        return f"{self.name}"
    @property
    def creator_mention(self) -> str: return f"<@{self.creator_id}>"
    @property
    def created_at_formatted(self) -> str: return f"<t:{self.created_at}:F>"
    @property
    def completed_formatted(self) -> str:
        if self.completed: resp = "+ COMPLETE +"
        else: resp = "- INCOMPLETE -"
        
        return (
            "```diff\n"
            f"{resp}"
            "\n```"
        )
    
    async def __delete_latest_history_entry(self) -> None:
        if self.checklist.resets == "DISABLED":
            await db.execute(
                "DELETE FROM CHECKLIST_HISTORY WHERE "
                f"item_id='{self.id}' AND completed_at>='0' "
                "LIMIT 1"
            )
            return
        
        await db.execute(
            "DELETE FROM CHECKLIST_HISTORY WHERE "
            f"item_id='{self.id}' AND completed_at>='{int(self.checklist.last_reset.timestamp())}'"
        )
    
    async def toggle_completion(self, u) -> None: await self.uncomplete(u) if self.completed else await self.complete(u)
    
    async def complete(self, u) -> None:
        if self.completed: return
        await u.increment_statistic('CHECKLIST_ITEMS_COMPLETED')
        await self.__delete_latest_history_entry()
        await db.execute(
            "INSERT INTO CHECKLIST_HISTORY (item_id,actor_id,completed_at) VALUES "
            f"('{self.id}', '{u.user.id}', '{int(time.time())}')"
        )
        await self.refresh()
        
    async def uncomplete(self, u) -> None:
        if not self.completed: return
        await u.increment_statistic('CHECKLIST_ITEMS_UNCOMPLETED')
        await self.__delete_latest_history_entry()
        await self.refresh()
    
    async def refresh(self) -> None:
        await self.__get_last_history()

    async def delete(self) -> None:
        await db.execute(
            "DELETE FROM CHECKLIST_ITEMS WHERE "
            f"item_id='{self.id}'"
        )
        await db.execute(
            "DELETE FROM CHECKLIST_HISTORY WHERE "
            f"item_id='{self.id}'"
        )
    
    async def edit(self, name: str, desc: str) -> None:
        if desc == "": desc = "NULL"
        else: desc = f"'{sanitize_name(desc)}'"
        
        await db.execute(
            f"UPDATE CHECKLIST_ITEMS SET name='{sanitize_name(name)}', description={desc} WHERE "
            f"item_id='{self.id}'"
        )
        self.name = name
        self.description = desc[1:-1] if desc != "NULL" else None

class ChecklistHistory:
    def __init__(
        self,
        item_name: str,
        item_id: str,
        actor_id: int,
        completed_at: int
    ) -> None:
        
        self.item_name = item_name
        self.item_id = item_id
        self.actor_id = actor_id
        self.completed_at = completed_at
        self.actor_mention = f"<@{actor_id}>"
        self.completed_at_formatted = f"<t:{completed_at}:F>"
    
    def __str__(self) -> str: return self.item_name

class Checklist:
    
    def __init__(
        self,
        id: str,
        emoji: str
    ) -> None:
        
        self.id = id
        self.emoji = emoji
        
    def __str__(self) -> str: return self.name
    
    async def ainit(self) -> None:
        self.server_id: int = None
        self.name: str = None
        self.description: str = None
        self.items: list[ChecklistItem] = []
        self.resets: str = "DISABLED"
        self.visible: bool = False
        self.created_at: int = None
        self.creator_id: int = None
        self.pos = 0
        await self.__get_checklist()
        await self.__get_items()
    
    async def __get_checklist(self) -> None:
        val = await db.execute(
            "SELECT server_id,name,description,reset,visible,created_at,creator_id FROM CHECKLISTS WHERE "
            f"checklist_id='{self.id}' LIMIT 1"
        )
        if val is None or val == []: return
        
        self.server_id = val[0][0]
        self.name = val[0][1]
        self.description = val[0][2]
        self.resets = val[0][3]
        self.__raw_visibility = val[0][4]
        self.created_at = val[0][5]
        self.creator_id = val[0][6]
    
    async def __get_items(self) -> None:
        self.visible = False # do not show up if all items complete or no items in list
        val = await db.execute(
            "SELECT checklist_id,item_id,creator_id,name,description,created_at,pos FROM "
            f"CHECKLIST_ITEMS WHERE checklist_id='{self.id}' "
            "ORDER BY pos ASC "
            f"LIMIT {tunables('MAX_ITEMS_PER_CHECKLIST')}"
        )
        if val is None or val == []:
            # self.visible = False # ignore database visibility if no items in list
            return
        for item in val:
            i = ChecklistItem(
                    checklist=self,
                    id=item[1],
                    creator_id=item[2],
                    name=item[3],
                    description=item[4],
                    created_at=item[5],
                    pos=item[6]
            )
            await i.ainit()
            if not i.completed and self.__raw_visibility == "TRUE": self.visible = True
            self.items.append(i)
    
    async def toggle_visibility(self) -> None:
        if self.__raw_visibility == "TRUE": visibility = "FALSE"
        else: visibility = "TRUE"
        await db.execute(
            f"UPDATE CHECKLISTS SET visible='{visibility}' "
            f"WHERE checklist_id='{self.id}'"
        )
        await self.ainit()
    
    async def create_item(self, u, name: str, desc: str = None) -> None:
        if desc == "": desc = "NULL"
        else: desc = f"'{sanitize_name(desc)}'"
        
        while True:
            iid = uuid.uuid4().hex
            if await db.execute(f"SELECT * FROM CHECKLIST_ITEMS WHERE item_id='{iid}'") in [[], None]: break
        
        # for pos + 1
        pos = await db.execute(f"SELECT pos FROM CHECKLIST_ITEMS WHERE checklist_id='{self.id}' ORDER BY pos DESC LIMIT 1")
        if pos is None or pos == []: pos = -1
        
        await db.execute(
            "INSERT INTO CHECKLIST_ITEMS (checklist_id,item_id,created_at,creator_id,name,description,pos) VALUES "
            f"('{self.id}', '{iid}', '{int(time.time())}', '{u.user.id}', '{sanitize_name(name)}', {desc}, '{pos+1}')"
        )
        await self.ainit()
    
    async def delete(self) -> None:
        for item in self.items: await item.delete()
        
        await db.execute(
            f"DELETE FROM CHECKLISTS WHERE checklist_id='{self.id}'"
        )
    
    async def set_resets(self, resets: str) -> None:
        await db.execute(
            f"UPDATE CHECKLISTS SET reset='{resets}' WHERE "
            f"checklist_id='{self.id}'"
        )
        await self.ainit()
    
    async def reorder_items(self, order: list) -> None:
        for i, id in enumerate(order):
            await db.execute(
                f"UPDATE CHECKLIST_ITEMS SET pos='{i}' WHERE "
                f"item_id='{id}'"
            )
        await self.ainit()
    
    async def edit(self, name: str, desc: str = None) -> None:
        if desc == "": desc = "NULL"
        else: desc = f"'{sanitize_name(desc)}'"
        
        await db.execute(
            f"UPDATE CHECKLISTS SET name='{sanitize_name(name)}', description={desc} WHERE "
            f"checklist_id='{self.id}'"
        )
        await self.ainit()

    @property
    async def history(self) -> list[ChecklistHistory]:
        val = await db.execute(
            "SELECT ci.name, ch.item_id, ch.actor_id, ch.completed_at FROM CHECKLIST_HISTORY AS ch "
            "INNER JOIN CHECKLIST_ITEMS AS ci ON "
            f"(ch.item_id=ci.item_id AND ci.checklist_id='{self.id}') "
            "ORDER BY completed_at DESC "
            f"LIMIT {tunables('MAX_VISIBLE_CHECKLIST_HISTORY')}"
        )
        if val is None or val == []: return []
        temp = []
        for item in val:
            temp.append(
                ChecklistHistory(
                    item_name=item[0],
                    item_id=item[1],
                    actor_id=item[2],
                    completed_at=item[3]
                )
            )
        return temp
    
    @property
    def resets_in(self) -> int|None:
        match self.resets:
            case "DAILY": return int((self.last_reset + timedelta(days=1)).timestamp())
            case "WEEKLY": return int((self.last_reset + timedelta(days=7)).timestamp())
            case "MONTHLY":                
                r = self.last_reset + timedelta(days=32)
                r = r.replace(day=1)
                return int((r).timestamp())
            case _: return None

    @property
    def last_reset(self) -> datetime:
        day = date.today()
        day = datetime.combine(day, datetime.min.time())
        
        
        match self.resets:
            
            case "DAILY": return day
                
            case "WEEKLY":
                dt = datetime.strptime(str(day), '%Y-%m-%d %H:%M:%S')
                start = dt - timedelta(days=dt.weekday())
                return start
                
            case "MONTHLY": return day.replace(day=1)
                
            case _: return 0
    
    @property
    def list_visibility_status(self) -> str:
        if self.visible: return (
            "```diff\n"
            "+ VISIBLE +\n"
            "```"
        )
        if self.__raw_visibility != "TRUE":
            reason = "Disabled by admin"
        elif len(self.items) > 0:
            reason = "All items have been completed."
        else:
            reason = "There are no items in this list."
        
        return (
            "```diff\n"
            "- NOT VISIBLE -\n"
            f"Reason: {reason}\n"
            "```"
        )
    
    @property
    def raw_visibility(self) -> bool: return True if self.__raw_visibility == "TRUE" else False
        
    
    @property
    def creator_mention(self) -> str: return f"<@{self.creator_id}>"
    @property
    def resets_in_timestamp(self) -> str: return f"<t:{self.resets_in}:R>"
    @property
    def bold_name_if_visible(self) -> str: return f"**{self.name}**" if self.visible else self.name



async def create_checklist(interaction: discord.Interaction, name: str, desc: str = None) -> None:
    if desc == "": desc = "NULL"
    else: desc = f"'{sanitize_name(desc)}'"
    
    while True:
        cid = uuid.uuid4().hex
        if await db.execute(f"SELECT * FROM CHECKLISTS WHERE checklist_id='{cid}'") in [[], None]: break
    
    pos = await db.execute(f"SELECT pos FROM CHECKLISTS WHERE server_id='{interaction.guild.id}' ORDER BY pos DESC LIMIT 1")
    if pos in [[], None]: pos = -1
    
    await db.execute(
        "INSERT INTO CHECKLISTS (server_id,created_at,creator_id,name,description,checklist_id,pos) VALUES "
        f"('{interaction.guild.id}', '{int(time.time())}', '{interaction.user.id}', '{sanitize_name(name)}', "
        f"{desc}, '{cid}', '{pos}')"
    )