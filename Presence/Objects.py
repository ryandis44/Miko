import asyncio
import time
import discord
import itertools
from Presence.GameActivity import GameActivity
from Database.ApplicationObjects import Application
# from Database.GuildObjects import MikoMember
from misc.misc import equal_tuples

PRESENCE_UPDATES = {}
PLAYTIME_SESSIONS = {}

class PresenceUpdate:
    
    def __init__(self, u, b: discord.Member, a: discord.Member, restored=False) -> None:
        self.u = u
        self.b = b # Before presence update
        self.a = a # After presence update
        self.restored = restored
    
    
    '''
    - self.__ensure_unique_update():
        - Works by ensuring no *duplicate* entries are processed
        - NO duplicates
        - Not thoroughly tested, but seems to work very well
        - Discards duplicate updates so a database call is only
          made for the first one
        * Could still allow duplicates, but very very rare
    
    - self.__presence_lock():
        - Works by ensuring all presence updates from an individual
          user are executed one at a time (in order of being received)
        - Has duplicates, but dupe detection code works here because
          each update is processed one at a time per user
        - Creates calls to the database for every duplicate update
    
    '''
    async def ainit(self) -> None:
        # if not self.__ensure_unique_update(): return # duplicate detection
        async with await self.__presence_lock():
            await self.__determine_update()
            
    
    async def __determine_update(self) -> None:
        if self.b.activities == self.a.activities or self.a.bot: return # Add scrape

        await ActivityUpdate(u=self.u, b=self.b, a=self.a, restored=self.restored).ainit()
    
    
    async def __presence_lock(self, release=False) -> asyncio.Lock:
        val = PRESENCE_UPDATES.get(self.u.user.id)
        
        if val is None:
            if release: return True
            lock = asyncio.Lock()
            PRESENCE_UPDATES[self.u.user.id] = {
                'at': int(time.time()),
                'lock': lock
            }
            return lock
        
        return val['lock']
        
    
    '''
    Function responsible for ensuring we do not process duplicate presence
    updates from users in multiple guilds with Miko.
    
    Check a hash (dict) table to see if user has had a presence update
    recently. If so, pull that update and check if it matches the update
    being checked. If it does, immediately stop processing this presence
    update, as it has already been processed.
    
    If there is no recent presence update, add the current update to
    a hash table containing the before and after presence updates, as
    well as the time we stored it to be used in comparison later.
    
    Time is stored for the 'presence_table_cleanup' function in
    async_processes.py to determine if that update needs to be
    deleted from cache. [Separate thread]
    - Presence updates older than 15 seconds are automatically deleted.
    '''
    def __ensure_unique_update(self) -> bool:
        try: val = PRESENCE_UPDATES[self.u.user.id]
        except: val = None
        
        if val is None:
            PRESENCE_UPDATES[self.u.user.id] = {
                'at': int(time.time()),
                'b': self.b.activities,
                'a': self.a.activities
            }
            return True


        '''
        If duplicate entries are still happening,
        revisit this code
        
        IF duplicates are still happening, place this
        code to be executed AFTER __sort_activities()
        '''
        if equal_tuples(val['b'], self.b.activities) and \
            equal_tuples(val['a'], self.a.activities):
                return False
        else:
            del PRESENCE_UPDATES[self.u.user.id]
            return self.__ensure_unique_update()


class ActivityUpdate:
    
    def __init__(self, u, b: discord.Member, a: discord.Member, restored=False) -> None:
        self.u = u
        self.b = {'user': b, 'playing': []} # Before presence update
        self.a = {'user': a, 'playing': []} # After presence update
        self.restored = restored
    
    async def ainit(self) -> None:
        self.__sort_activities()
        
        if await self.u.track_playtime:
            await self.__playing_init()
    
    
    # Sort all user activities into dicts
    # that identify their type.
    #
    # Other activity types would be added
    # here to be sorted.
    #
    # This function currently only identifies
    # 'playing' type activities
    def __sort_activities(self) -> None:
        for b_activity, a_activity in itertools.zip_longest(self.b['user'].activities, self.a['user'].activities):
            b_activity: discord.Activity
            a_activity: discord.Activity
            try:
                if b_activity.type is discord.ActivityType.playing:
                    self.b['playing'].append({
                            'activity': b_activity,
                            'name': b_activity.name,
                            'app': None
                        })
                else: raise Exception
            except: self.b['playing'].append(None)

            try:
                if a_activity.type is discord.ActivityType.playing:
                    self.a['playing'].append({
                            'activity': a_activity,
                            'name': a_activity.name,
                            'app': None
                        })
                else: raise Exception
            except: self.a['playing'].append(None)

        
        '''
        This block of code is responsible for reordering both arrays and ensuring the
        indexes match each other.
        
        i.e.
        arr1 = [{'app': VSCode}, {'app': Minecraft}]
        arr2 = [{'app': Minecraft}, {'app': VScode}]
        to
        arr2 = [{'app': VSCode}, {'app': Minecraft}]
        '''
        for i in range(len(self.b['playing'])):
            for j in range(len(self.a['playing'])):
                if self.b['playing'][i] and self.a['playing'][j] and \
                    self.b['playing'][i]['name'] == self.a['playing'][j]['name']:
                        self.a['playing'][i], self.a['playing'][j] = self.a['playing'][j], self.a['playing'][i]


    
    '''
    PLAYTIME TRACKING 3.0
    
    Function responsible for all playtime tracking. All 'playing'
    activities get processed by this function. It will decide
    whether to start, stop, or continue tracking.
    
    Broken up into parts:
    
    1. Determine activity attributes, including 'Application' object
    2. Determine if user has started, stopped, or is continuing this
       activity.
    3. Store, remove, or check dict (hash table) containing all
       active playtime sessions.
       
    self.b/self.a Dictionary map:
    - user: discord.Member: user
    - playing: list: list of dicts of playing activities
    
    '''
    async def __playing_init(self) -> None:
        await self.__get_activity_attributes() # 1.
        await self.__determine_status() # 2. and 3.
        
        # Debug code to print active applications
        # for i, user in enumerate([self.b, self.a]):
        #     for a in user['playing']:
        #         if a is None: continue
        #         print(f"{i+1}. {a['app']}")
        # print('\n\n')
        
    
    async def __create_session(self, activity) -> None:
        # Initialize sessions dict under user ID in
        # PLAYTIME_SESSIONS
        try: val = PLAYTIME_SESSIONS[self.u.user.id]
        except: val = None
        g = GameActivity(u=self.u, activity=activity, restored=self.restored)
        
        
        # If there IS NOT an active sessions
        # list for this user
        if val is None:
            await g.ainit()
            g.test = "Turds"
            PLAYTIME_SESSIONS[self.u.user.id] = {
                'sessions': {activity['app'].id: g}
            }
        
        # If there IS an active sessions
        # list for this user
        else:
            try: val = val['sessions'][activity['app'].id]
            except: pass
            
            # If there IS an active Playtime session
            # for this user and this app id
            if type(val) == GameActivity:
                if val.app != activity['app']:
                    await self.__end_session(val.app)
                    await self.__create_session(activity)
                else: print("**DUPLICATE UPDATE DETECTED, doing nothing**")
            
            # If there IS NOT an active Playtime session
            # for this user and this app id
            else:
                await g.ainit()
                PLAYTIME_SESSIONS[self.u.user.id]['sessions'][activity['app'].id] = g
    
    async def __end_session(self, app: Application) -> None:
        try: val = PLAYTIME_SESSIONS[self.u.user.id]['sessions'][app.id]
        except: return
        val: GameActivity
        await val.end()
        del PLAYTIME_SESSIONS[self.u.user.id]['sessions'][app.id]
        
        # Cleanup
        if len(PLAYTIME_SESSIONS[self.u.user.id]['sessions']) == 0:
            del PLAYTIME_SESSIONS[self.u.user.id]
    
    async def __session_heartbeat(self, activity) -> bool:
        try: g: GameActivity = PLAYTIME_SESSIONS[self.u.user.id]['sessions'][activity['app'].id]
        except: return False
        await g.refresh(activity)
            
            
            
    async def __determine_status(self) -> None:
        global PLAYTIME_SESSIONS
        
        
        for b_activity, a_activity in itertools.zip_longest(self.b['playing'], self.a['playing']):
            
            # If not playing
            if b_activity is None and a_activity is not None:
                print("**STARTED ACTIVITY**")
                await self.__create_session(a_activity)
                continue
            
            if b_activity is not None and a_activity is None:
                print("**STOPPED ACTIVITY**")
                await self.__end_session(b_activity['app'])
                continue
            
            if b_activity is not None and a_activity is not None:
                print("**ACTIVITY HEARTBEAT**")
                if b_activity['app'] == a_activity['app']:
                    
                    # This check is to ensure we are tracking the activity
                    # that has not changed.
                    if not await self.__session_heartbeat(a_activity):
                        await self.__create_session(a_activity)
                        await self.__session_heartbeat(a_activity)
                    continue
                
                else:
                    # stop b_activity and start a_activity. Activity has changed
                    print("**ACTIVITY CHANGED**")
                    await self.__end_session(b_activity['app'])
                    await self.__create_session(a_activity)
                    continue
                
                
                
    
    
    # Get application ID, session ID, start time, and
    # activity name, if applicable
    async def __get_activity_attributes(self) -> None:
        for user in [self.b, self.a]:
            for app in user['playing']:
                if app is None: continue
                try: app['start_time'] = int(app['activity'].start.timestamp())
                except: app['start_time'] = None
                try: app['session_id'] = str(app['activity'].session_id)
                except: app['session_id'] = None
                try: app['name'] = str(app['activity'].name)
                except: app['name'] = None
                try: app['app_id'] = str(app['activity'].application_id)
                except: app['app_id'] = None
                
                app['app'] = await self.__identify_app(app=app)
                
    # Generates an 'Application' object if the user
    # has any 'playing' status
    async def __identify_app(self, app) -> Application:
        a = Application(app=app)
        await a.ainit()
        return a
    
    