from datetime import date, datetime, timedelta, timezone
import time
from Database.database_class import AsyncDatabase
db = AsyncDatabase("YMCA.Checklist.Objects.py")



class ChecklistItem:

    def __init__(
        self,
        checklist,
        id: str,
        creator_id: int,
        name: str,
        description: str
    ) -> None:
        
        self.checklist = checklist
        self.id = id
        self.creator_id = creator_id
        self.name = name
        self.description = description
        self.completed_at: int = None
        self.actor_id: int = None
    
    def __str__(self) -> str:
        return f"{self.name} ({self.id}) [{self.checklist.name}]"
    
    async def ainit(self) -> None:
        await self.__get_last_history()
        
    async def __get_last_history(self) -> None:
        val = await db.execute(
            "SELECT actor_id,completed_at FROM CHECKLIST_HISTORY WHERE "
            f"item_id='{self.id}'"
        )
        if val == [] or val is None: return
        self.actor_id = val[0][0]
        self.completed_at = val[0][1]
    
    @property
    def completed(self) -> bool:
        
        last_reset = self.checklist.last_reset
        if type(last_reset) != int: last_reset = int(last_reset.timestamp())
        if self.name == "mop n stuff":
            print(last_reset)
        
        if self.completed_at is not None and self.completed_at >= last_reset: return True
        return False
    
    async def __delete_history_entry(self) -> None:
        await db.execute(
            "DELETE FROM CHECKLIST_HISTORY WHERE "
            f"item_id='{self.id}' AND completed_at>='{int(self.checklist.last_reset.timestamp())}'"
        )
    
    async def complete(self, user_id: int) -> None:
        if self.completed: return
        print(f"Completed {self}")
        await self.__delete_history_entry()
        await db.execute(
            "INSERT INTO CHECKLIST_HISTORY (item_id,actor_id,completed_at) VALUES "
            f"('{self.id}', '{user_id}', '{int(time.time())}')"
        )
        
    
    async def uncomplete(self) -> None:
        if not self.completed: return
        print(f"Uncompleted {self}")

    async def delete(self) -> None:
        pass
    
    async def edit(self) -> None:
        pass


class Checklist:
    
    def __init__(
        self,
        id: str,
        emoji: str
    ) -> None:
        
        self.id = id
        self.emoji = emoji
        self.server_id: int = None
        self.name: str = None
        self.description: str = None
        self.items: list[ChecklistItem] = []
        self.resets: str = "DISABLED"
        self.visible: bool = False
        
    
    async def ainit(self) -> None:
        await self.__get_checklist()
        await self.__get_items()
    
    async def __get_checklist(self) -> None:
        val = await db.execute(
            "SELECT server_id,name,description,reset,visible FROM CHECKLISTS WHERE "
            f"checklist_id='{self.id}' LIMIT 1"
        )
        if val is None or val == []: return
        
        self.server_id = val[0][0]
        self.name = val[0][1]
        self.description = val[0][2]
        self.resets = val[0][3]
        self.visible = True if val[0][4] == "TRUE" else False
    
    async def __get_items(self) -> None:
        val = await db.execute(
            "SELECT checklist_id,item_id,creator_id,name,description FROM "
            f"CHECKLIST_ITEMS WHERE checklist_id='{self.id}'"
        )
        if val is None or val == []:
            self.visible = False # ignore database visibility if no items in list
            return
        for item in val:
            i = ChecklistItem(
                    checklist=self,
                    id=item[1],
                    creator_id=item[2],
                    name=item[3],
                    description=item[4]
            )
            await i.ainit()
            self.items.append(i)
    
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
        day = f"{date.today()}"
        day = f"2023-05-17"
        match self.resets:
            
            case "DAILY":
                dt = datetime.strptime(day, '%Y-%m-%d')
                dt = dt + timedelta(days=1)
                dt = dt.replace(tzinfo=timezone.utc)
                start = dt - timedelta(days=dt.weekday() + 1) # was set to 1 for Plex, double check later
                end = start + timedelta(days=6)
                end = str(end).split()
                val = datetime.strptime(end[0], "%Y-%m-%d")
                return val
                
            case "WEEKLY":
                dt = datetime.strptime(day, '%Y-%m-%d')
                dt = dt + timedelta(days=1)
                dt = dt.replace(tzinfo=timezone.utc)
                start = dt - timedelta(days=dt.weekday() + 0) # was set to 1 for Plex, double check later
                end = start + timedelta(days=7)
                start = str(start).split()
                end = str(end).split()
                val = datetime.strptime(start[0], "%Y-%m-%d")
                return val
                
            case "MONTHLY":
                
                dt = datetime.strptime(day, '%Y-%m-%d')
                dt = dt.replace(tzinfo=timezone.utc)
                dt = dt.replace(day=1)
                start = dt - timedelta(days=dt.weekday() + 0) # was set to 1 for Plex, double check later
                end = start + timedelta(days=0)
                start = str(start).split()
                end = str(end).split()
                val = datetime.strptime(end[0], "%Y-%m-%d")
                return val
                
            case _: return 0
