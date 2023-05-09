from Database.database_class import AsyncDatabase
db = AsyncDatabase("YMCA.Checklist.Objects.py")



class ChecklistItem:

    def __init__(
        self,
        checklist_id: str,
        id: str,
        creator_id: int,
        name: str,
        description: str,
        completed_at: int,
    ) -> None:
        
        self.checklist_id = checklist_id
        self.id = id
        self.creator_id = creator_id
        self.name = name
        self.description = description
        self.completed_at = completed_at
    
    def completed(self) -> bool:
        return True if self.id == "df0c3220672b4ab99b970d82b3f58fce" else False
    
    async def complete(self) -> None:
        pass

    async def delete(self) -> None:
        pass
    
    async def edit(self) -> None:
        pass


class Checklist:
    
    def __init__(
        self,
        id: str
    ) -> None:
        
        self.id = id
        self.server_id: int = None
        self.name: str = None
        self.description: str = None
        self.items: list[ChecklistItem] = []
        self.resets: str = "DISABLED"
        
    
    async def ainit(self) -> None:
        await self.__get_checklist()
        await self.__get_items()
    
    async def __get_checklist(self) -> None:
        val = await db.execute(
            "SELECT server_id,name,description,resets FROM CHECKLISTS WHERE "
            f"checklist_id='{self.id}' LIMIT 1"
        )
        if val is None or val == []: return
        
        self.server_id = val[0][0]
        self.name = val[0][1]
        self.description = val[0][2]
        self.resets = val[0][3]
    
    async def __get_items(self) -> None:
        val = await db.execute(
            "SELECT checklist_id,item_id,creator_id,name,description,completed_at FROM "
            f"CHECKLIST_ITEMS WHERE checklist_id='{self.id}'"
        )
        if val is None or val == []: return []
        for item in val:
            self.items.append(
                ChecklistItem(
                    checklist_id=item[0],
                    id=item[1],
                    creator_id=item[2],
                    name=item[3],
                    description=item[4],
                    completed_at=item[5]
                )
            )

