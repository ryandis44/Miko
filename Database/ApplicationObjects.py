import uuid
from Database.database_class import AsyncDatabase
db = AsyncDatabase('Database.ApplicationObjects.py')


'''
Part of Playtime 3.0

Class responsible for storing and fetching applications in the database.

Class will pull application from database and all of its attributes and
will update the name of the application if:
    1) It has a discord app ID
    2) The name on discord is different than the database (name change)

'''
class Application:
    
    def __init__(self, app):
        self.__raw_app = app
    
    async def ainit(self) -> None:
        await self.__check_database()
        self.__assign_attributes()
        # update app with discord ID
    
    def __str__(self) -> str:
        return f"Application: {self.name} | {self.id} | {self.emoji}"

    def __eq__(self, __value: object) -> bool:
        return self.id == __value.id
    
    def __assign_attributes(self) -> None:
        self.name: str = self.__val[0]
        self.id: str = self.__val[1]
        self.discord_id: bool = True if self.__val[2] == "TRUE" else False
        self.counts_towards_playtime: bool = True if self.__val[3] == "TRUE" else False
        self.emoji: str = self.__val[4]
    
    async def __check_database(self) -> None:
        if self.__raw_app['app_id'] is not None:
            where = f"app_id='{self.__raw_app['app_id']}'"
        else: where = f"name='{self.__raw_app['name']}'"
        
        while True:
            self.__val = await db.execute(
                "SELECT name,app_id,has_discord_id,counts_towards_playtime,emoji "
                "FROM APPLICATIONS WHERE "
                f"{where} "
                "LIMIT 1"
            )
            if self.__val is None or self.__val == []:
                await self.__create_application(self)
            else:
                self.__val = self.__val[0]
                break
        
    
    async def __create_application(self) -> None:
        aid = await self.__generate_id() if self.__raw_app['app_id'] is None \
            else self.__raw_app['app_id']
        await db.execute(
            "INSERT INTO APPLICATIONS "
            "(name, app_id, has_discord_id) VALUES "
            f"('{self.__raw_app['name']}', "
            f"'{aid}', "
            f"'{'FALSE' if self.__raw_app['app_id'] is None else 'TRUE'}')"
        )
    
    async def __generate_id(self) -> str:
        while True:
            aid = uuid.uuid4().hex
            val = await db.execute(f"SELECT * FROM APPLICATIONS WHERE app_id='{aid}'")
            if val == []: break
        return aid