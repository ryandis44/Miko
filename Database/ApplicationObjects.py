import uuid
from Database.database_class import AsyncDatabase
from tunables import *
db = AsyncDatabase('Database.ApplicationObjects.py')


'''
Part of Playtime 3.0

Class responsible for storing and fetching applications in the database.

Class will pull application from database and all of its attributes and
will update the name of the application if:
    1) It has a discord app ID
    2) The name on discord is different than the database (name change)

'''
class PartialApplication:
    def __init__(self) -> None:
        pass

class Application:
    
    def __init__(self, app):
        self.__raw_app = app
        self.blacklisted_id = False
        
        try: l = tunables('BLACKLISTED_APPLICATION_IDS').split(' ')
        except: l = [tunables('BLACKLISTED_APPLICATION_IDS')]
        if self.__raw_app['app_id'] in l:
            self.blacklisted_id = app['app_id']
            self.__raw_app['app_id'] = None
    
    async def ainit(self) -> None:
        await self.__check_database()
        await self.__assign_attributes()
    
    def __str__(self) -> str:
        return f"Application: {self.name} | {self.id} | {self.emoji}"

    def __eq__(self, __value: object) -> bool:
        try: return self.id == __value.id
        except: return False
    
    @property
    async def counts_towards_playtime(self) -> bool:
        val = await db.execute(
            "SELECT counts_towards_playtime FROM APPLICATIONS WHERE "
            f"{self.where} "
            "LIMIT 1"
        )
        if val == "TRUE": return True
        return False
    
    async def __assign_attributes(self) -> None:
        self.name: str = self.__val[0]
        self.id: str = self.__val[1]
        self.discord_id: bool = True if self.__val[2] == "TRUE" else False
        self.emoji: str = self.__val[3]
        if self.blacklisted_id:
            self.blacklisted_id = f"{self.blacklisted_id} -> {self.id}"
        
        if self.__raw_app['app_id'] is None: return
        
        if self.name != self.__raw_app['name']:
            await db.execute(
                f"UPDATE APPLICATIONS SET name='{sanitize_name(self.__raw_app['name'])}' "
                f"WHERE app_id='{self.id}'"
            )
            self.name = self.__raw_app['name']
    
    async def __check_database(self) -> None:
        if self.__raw_app['app_id'] is not None:
            self.where = f"app_id='{self.__raw_app['app_id']}'"
        else: self.where = f"name='{sanitize_name(self.__raw_app['name'])}'"
        
        while True:
            self.__val = await db.execute(
                "SELECT name,app_id,has_discord_id,emoji "
                "FROM APPLICATIONS WHERE "
                f"{self.where} "
                "LIMIT 1"
            )
            if self.__val is None or self.__val == []:
                await self.__create_application()
            else:
                self.__val = self.__val[0]
                break
        
    
    async def __create_application(self) -> None:
        aid = await self.__generate_id() if self.__raw_app['app_id'] is None \
            else self.__raw_app['app_id']
        await db.execute(
            "INSERT INTO APPLICATIONS "
            "(name, app_id, has_discord_id) VALUES "
            f"('{sanitize_name(self.__raw_app['name'])}', "
            f"'{aid}', "
            f"'{'FALSE' if self.__raw_app['app_id'] is None else 'TRUE'}')"
        )
    
    async def __generate_id(self) -> str:
        while True:
            aid = uuid.uuid4().hex
            val = await db.execute(f"SELECT * FROM APPLICATIONS WHERE app_id='{aid}'")
            if val == []: break
        return aid