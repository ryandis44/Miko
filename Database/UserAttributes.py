from Database.ApplicationObjects import Application
from Presence.GameActivity import GameActivity
from misc.misc import time_elapsed, today
from tunables import tunables
from Database.database_class import AsyncDatabase
db = AsyncDatabase("Database.UserAttributes.py")

#temporary
from Presence.playtime import sessions_hash_table

class Playtime:
    def __init__(self, u):
        self.u = u
    
    ############# REDO ########################
    # Returns total playtime since Miko began
    # tracking this user
    @property
    async def total(self):
        val = await db.execute(
            "SELECT playtime FROM TOTAL_PLAYTIME "
            f"WHERE user_id='{self.u.user.id}'"
        )
        if val is None or val == []: return 0
        return int(val)
    ###########################################
    
    # Returns total playtime today, as int
    @property
    async def playtime_today(self) -> int:
        playtime_before_midnight = await db.execute(
            f"SELECT SUM(ph.end_time - {today()}) "
            "FROM PLAY_HISTORY AS ph "
            "INNER JOIN APPLICATIONS AS a ON "
            "(ph.app_id=a.app_id AND counts_towards_playtime!='FALSE') "
            f"WHERE ph.user_id={self.u.user.id} AND ph.end_time!=-1 AND ph.end_time>={today()} AND (ph.end_time - ph.start_time)>={tunables('THRESHOLD_LIST_GAME_ACTIVITY')} "
            f"AND ph.start_time<{today()}"
        )
        playtime_after_midnight = await db.execute(
            f"SELECT SUM(ph.end_time - start_time) "
            "FROM PLAY_HISTORY AS ph "
            "INNER JOIN APPLICATIONS AS a ON "
            f"(ph.app_id=a.app_id AND counts_towards_playtime!='FALSE') AND (ph.end_time - ph.start_time)>={tunables('THRESHOLD_LIST_GAME_ACTIVITY')} "
            f"WHERE user_id={self.u.user.id} AND end_time!=-1 AND start_time>={today()}"
        )
        if playtime_after_midnight is None: playtime_after_midnight = 0
        if playtime_before_midnight is None: playtime_before_midnight = 0
        return playtime_before_midnight + playtime_after_midnight
    
    # Returns GameActivity object if game found, else None
    @property
    async def playing(self) -> GameActivity:
        global sessions_hash_table
        try:
            app: GameActivity = sessions_hash_table.get_val(self.u.user.id)
            if not await app.is_listed: return [False, 1, -1, ":question:"]

            return [
                True,
                app.start_time,
                app.act_name,
                await app.emoji
            ]
        except: # If we do not have the session stored in the hash table, we are not tracking it. Don't list
            return [False, 1, -1, ":question:"]
    
    # Total number of (listable) playtime sessions
    @property
    async def total_entries(self) -> int:
        val = await db.execute(
            "SELECT COUNT(*) FROM ("
            "SELECT a.emoji, ph.end_time, a.name, (ph.end_time - ph.start_time) AS total "
            "FROM PLAY_HISTORY AS ph "
            "INNER JOIN APPLICATIONS AS a ON "
            "(ph.app_id=a.app_id AND counts_towards_playtime!='FALSE') "
            f"WHERE ph.user_id={self.u.user.id} AND ph.end_time!=-1 AND (ph.end_time - ph.start_time)>={tunables('THRESHOLD_LIST_GAME_ACTIVITY')} "
            ") AS q"
        )
        if val is None or val == []: return 0
        return int(val)
    
    ################ REDO ####################
    # Returns average playtime session
    @property
    async def average_session(self) -> str:
        val = await db.execute(
            "SELECT avg FROM AVERAGE_PLAYTIME WHERE "
            f"user_id='{self.u.user.id}'"
        )
        if val is None or val == []: return "0s"
        return time_elapsed(int(val), 'h')
    ##########################################
            
    # Returns recent playtime entries based off
    # limit and offset
    async def recent(self, limit, offset) -> list:
        val = await db.execute(
            "SELECT a.emoji, ph.end_time, a.name, (ph.end_time - ph.start_time) AS total "
            "FROM PLAY_HISTORY AS ph "
            "INNER JOIN APPLICATIONS AS a ON "
            "(ph.app_id=a.app_id AND counts_towards_playtime!='FALSE') "
            f"WHERE ph.user_id={self.u.user.id} AND ph.end_time!=-1 AND (ph.end_time - ph.start_time)>={tunables('THRESHOLD_LIST_GAME_ACTIVITY')} "
            f"ORDER BY ph.end_time DESC LIMIT {limit} OFFSET {offset}"
        )
        if val is None or val == []: return None
        return val
    
    # Returns the end_time (last time played) of
    # specified app_id
    async def last_played(self, app_id) -> int:
        val = await db.execute(
            f"SELECT end_time FROM PLAY_HISTORY WHERE "
            f"user_id={self.u.user.id} AND app_id='{app_id}' AND end_time!=-1 "
            "ORDER BY end_time DESC LIMIT 1"
        )
        if val is None or val == []: return 0
        return val