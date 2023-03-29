''' Playtime activity tracking 2.0

This class handles all playtime tracking. The purpose of this class is to optimize storing, tracking,
resuming, and restoring playtime sessions.

This class works by first being stored in a hash map with the key being the user id of the user that
started an activity.

Once this class is created, we will check 2 things:
    - Can this entry be:
        * Restored (bot restarts while a session is active)
        * Resumed (user ends and restarts session with same game within 10 minutes)

If we can restore the session, we will simply add it back to our hash map and resume tracking the
activity until a change occurs.

Resuming the session is significantly different than restoring it. There are several criteria that
the activity must "go through" in order to be resumed. Here is the logic:

    * Example case: A user was playing a game for a certain amount of time and their game crashed.
                    they resume the same game within 10 minutes of their game crashing.
        - This session will be restored because:
            * The user started a "new" session of the same game less than 10 minutes after ending
              their last session.
    
    * Some other logic:
        - Playtime entries that have the same session id and app id are resumed regardless of end time.

        - Bot goes down for longer than 10 minutes (or connection is lost; or user goes invisible/hides
          activity status) but the activity, as tracked by discord, has the same start time as the entry
          we have stored in the database, resume activity. We can be sure this is the same activity
          because it has the same start time as what we already have stored.

        - When a session is resumed (based off example case 1), the activity on discord does not have the
          same start time. We will store this time as 'resume_time' in our database so we can continually
          resume that session
'''

import time
import discord
from Database.database_class import AsyncDatabase, Database
from tunables import *


# ga = Database("GameActivity.py")
db = AsyncDatabase("Playtime.GameActivity.py")
sdb = Database("Playtime.GameActivity.py")

class GameActivity:
    def __init__(self, user, app_id, i, st=None) -> None:
        self.i = i
        self.user: discord.Member = user
        self.app_id = app_id
        self.resume_time = None
        self.session_id = self.__sesh_id()
        if st is None:
            self.start_time = self.__original_start_time()
            self.restored = False
            self.__resume_time = int(time.time()) - tunables('THRESHOLD_RESUME_GAME_ACTIVITY')
        else:
            self.start_time = st
            self.restored = True
            self.__resume_time = int(time.time()) - tunables('THRESHOLD_RESUME_REBOOT_GAME_ACTIVITY')
        self.act_name = self.__activity_name()
    
    async def ainit(self) -> None:
        await self.__new_activity_entry()

    @property
    def get_id(self) -> int:
        return self.user.id
    @property
    def get_user(self) -> discord.Member:
        return self.user
    @property
    def get_start(self) -> int:
        return int(self.start_time)
    @property
    def get_app_id(self) -> str:
        return self.app_id
    @property
    def get_app_name(self) -> str:
        return self.act_name
    @property
    def get_session_id(self) -> str:
        return self.session_id
    @property
    def get_resume_time(self) -> int:
        return self.resume_time
    @property
    def is_restored(self) -> bool:
        return self.restored
    @property
    def is_resumed(self) -> bool:
        if self.resume_time is None: return False
        else: return True
    @property
    async def is_listed(self) -> bool:
        sel_cmd = f"SELECT counts_towards_playtime FROM APPLICATIONS WHERE app_id='{self.app_id}'"
        val = await db.execute(sel_cmd)
        if val == "FALSE": return False
        return True
    @property
    async def emoji(self):
        first = True
        sel_cmd = []
        sel_cmd.append(f"SELECT emoji FROM APPLICATIONS WHERE")

        if type(self.app_id) is list:
            for id in self.app_id:
                if first:
                    sel_cmd.append(f" (app_id='{id[0]}' ")
                    first = False
                else:
                    sel_cmd.append(f"OR app_id='{id[0]}'")
            sel_cmd.append(") ")
        else:
            sel_cmd.append(f" app_id='{self.app_id}' ")
        
        sel_cmd.append(f"AND emoji!=':video_game:' LIMIT 1")

        emoji = await db.execute(''.join(sel_cmd))
        if emoji is None: return ":question:"
        elif emoji == []: return ":video_game:"
        return emoji 

    def __sesh_id(self):
        try: return self.user.activities[self.i].session_id
        except: return None
    
    def __original_start_time(self):
        try: return int(self.user.activities[self.i].start.timestamp())
        except: return int(time.time())
    
    def __activity_name(self):
        try: return str(self.user.activities[self.i].name)
        except: None

    # Object gets created when activity is started,
    # so update database accordingly
    async def __new_activity_entry(self, attempt=1):
        
        # Verify there is not already an entry. If there is, "reactivate" it
        sel_cmd = []
        sel_cmd.append(f"SELECT start_time,end_time,resume_time FROM PLAY_HISTORY WHERE user_id='{self.user.id}' AND app_id='{self.app_id}' ")

        # Session ID > Start time; Session ID guarantees identifying a unique session over a session start time
        # If the user starts a new session of the same game they stopped playing 10>= minutes ago, resume that
        # session.
        if self.session_id is None: sel_cmd.append(f"AND ((start_time='{self.start_time}' OR resume_time='{self.start_time}') OR end_time>='{self.__resume_time}') ")
        else: sel_cmd.append(f"AND session_id='{self.session_id}' ")
        sel_cmd.append("LIMIT 1")
        
        val = await db.execute(''.join(sel_cmd))
        if val != []: self.resume_time = val[0][2]
        if val == []:
            ins_cmd = []
            ins_cmd.append(f"INSERT INTO PLAY_HISTORY (user_id, app_id, start_time")
            if self.session_id is not None: ins_cmd.append(", session_id) ")
            else: ins_cmd.append(") ")
            ins_cmd.append(f" VALUES ('{self.user.id}', '{self.app_id}', '{self.start_time}'")
            if self.session_id is not None: ins_cmd.append(f", '{self.session_id}')")
            else: ins_cmd.append(")")
            await db.execute(''.join(ins_cmd))
            
        # If start time is the same, resume
        #
        # Example case:
        # - User has been playing a game for several hours (or any amount of time)
        #   and Miko goes down for longer than the 10m window of session restoration.
        #   Using the start time, we can accurately resume the same session within
        #   miko
        elif int(val[0][0]) == self.start_time:
            upd_cmd = []
            upd_cmd.append(f"UPDATE PLAY_HISTORY SET end_time='-1' WHERE user_id='{self.user.id}' AND app_id='{self.app_id}' AND start_time='{self.start_time}'")
            if self.session_id is not None: upd_cmd.append(f" AND session_id='{self.session_id}'")
            await db.execute(''.join(upd_cmd))
        
        # Resume if ended 10m>= ago
        # If the row has an end time that ended less than 5m ago
        #
        # Example case:
        # - User was playing a game (for any amount of time) and their
        #   crashes. They restart the game within 10m; resume the original
        #   session
        elif int(val[0][1]) >= self.__resume_time:
            self.resume_time = self.start_time
            self.start_time = val[0][0]
            upd_cmd = []
            upd_cmd.append(f"UPDATE PLAY_HISTORY SET end_time='-1', resume_time='{self.resume_time}'")
            if self.session_id is not None: upd_cmd.append(f", session_id='{self.session_id}'")
            upd_cmd.append(f" WHERE user_id='{self.user.id}' AND app_id='{self.app_id}' AND start_time='{self.start_time}'")
            await db.execute(''.join(upd_cmd))
        
        # Resume if resume_time is equal to start time
        # If our resume time equals the start time of the current activity
        #
        # Example case:
        # - User was playing a game, stopped, and started within 10m but then
        #   hid their online status for more than 10m. This prevents creating
        #   a duplicate session that would start before the last (resumed)
        #   session ended
        elif int(val[0][2]) == self.start_time:
            self.resume_time = self.start_time
            self.start_time = val[0][0]
            upd_cmd = []
            upd_cmd.append(f"UPDATE PLAY_HISTORY SET end_time='-1' WHERE user_id='{self.user.id}' AND app_id='{self.app_id}' AND start_time='{self.start_time}'")
            if self.session_id is not None: upd_cmd.append(f" AND session_id='{self.session_id}'")
            await db.execute(''.join(upd_cmd))


        # Verify a database entry has been made. If not, recurse and try again.
        val = await db.execute(''.join(sel_cmd))
        if val == [] and not attempt >= 5 and self.resume_time is None:
            await self.__new_activity_entry(attempt + 1) # Only try 5 times
        elif attempt >= 5: self.__end_session() # Cannot create database entry, abort tracking this activity entirely


    # Close activity entry in database and delete object
    async def close_activity_entry(self, keep_sid=False, current_time=None):
        if current_time is None: current_time = int(time.time())
        
        # Unlike 1.0, if a class is made then a database entry has also been made.
        upd_cmd = []
        if keep_sid: sid = ""
        else: sid = "session_id=NULL, "
        upd_cmd.append(
            f"UPDATE PLAY_HISTORY SET {sid}end_time='{current_time}' WHERE "+
            f"user_id='{self.user.id}' AND app_id='{self.app_id}' AND end_time='-1' AND start_time='{self.start_time}' "
        )
        if self.session_id is not None: upd_cmd.append(f"AND session_id='{self.session_id}' ")
        upd_cmd.append("ORDER BY start_time DESC LIMIT 1")
        await db.execute(''.join(upd_cmd))

        self.__end_session()
        return


    # Bandaid function for synchronous shutdown
    def close_activity_entry_synchronous(self, keep_sid=False, current_time=None):
        if current_time is None: current_time = int(time.time())
        
        # Unlike 1.0, if a class is made then a database entry has also been made.
        upd_cmd = []
        if keep_sid: sid = ""
        else: sid = "session_id=NULL, "
        upd_cmd.append(
            f"UPDATE PLAY_HISTORY SET {sid}end_time='{current_time}' WHERE "+
            f"user_id='{self.user.id}' AND app_id='{self.app_id}' AND end_time='-1' AND start_time='{self.start_time}' "
        )
        if self.session_id is not None: upd_cmd.append(f"AND session_id='{self.session_id}' ")
        upd_cmd.append("ORDER BY start_time DESC LIMIT 1")
        sdb.db_executor(''.join(upd_cmd))

        self.__end_session()
        return

    async def update_session_id(self):
        sid = self.sesh_id()
        if sid is not None and sid != self.session_id:
            self.session_id = sid
            upd_cmd = (
                f"UPDATE PLAY_HISTORY SET session_id='{self.session_id}' WHERE "+
                f"user_id='{self.user.id}' AND app_id='{self.app_id}' AND end_time='-1' AND start_time='{self.start_time}' "+
                "ORDER BY start_time DESC LIMIT 1"
            )
            await db.execute(upd_cmd)

    def __end_session(self):
        del self # Delete class object