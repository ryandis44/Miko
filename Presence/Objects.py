import discord
import itertools
from Presence.GameActivity import GameActivity
from Database.GuildObjects import MikoMember
from Database.ApplicationObjects import Application

PLAYTIME_SESSIONS = {}

class PresenceUpdate:
    
    def __init__(self, u: MikoMember, b: discord.Member, a: discord.Member) -> None:
        self.u = u
        self.b = b # Before presence update
        self.a = a # After presence update
    
    async def ainit(self) -> None:
        await self.__determine_update()
    
    async def __determine_update(self) -> None:
        if self.b.activities == self.a.activities or self.a.bot: return # Add scrape
        
        # We know an activity update has happened, create class
        await ActivityUpdate(u=self.u, b=self.b, a=self.a).ainit()


class ActivityUpdate:
    
    def __init__(self, u: MikoMember, b: discord.Member, a: discord.Member) -> None:
        self.u = u
        self.b = {'user': b, 'playing': []} # Before presence update
        self.a = {'user': a, 'playing': []} # After presence update
    
    async def ainit(self) -> None:
        self.__sort_activities()
        
        if await self.u.track_playtime:
            await self.__playing_init()
    
    
    # Sort all user activities into dicts
    # that identify their type.
    #
    # Other activity types would be added
    # here to be sorted.
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
        indexes match eachother.
        
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
        
        # for i, user in enumerate([self.b, self.a]):
        #     for a in user['playing']:
        #         if a is None: continue
        #         print(f"{i+1}. {a['app']}")
        # print('\n\n')
        
    
    async def __create_session(self, activity) -> None:
        try: val = PLAYTIME_SESSIONS[self.u.user.id]
        except: val = None
        g = GameActivity(u=self.u, activity=activity)
        
        # Initialize sessions dict under user ID in
        # PLAYTIME_SESSIONS
        if val is None:
            await g.ainit()
            PLAYTIME_SESSIONS[self.u.user.id] = {
                'sessions': {activity['app'].id: g}
            }
        else:
            try: val = val['sessions'][activity['app'].id]
            except: pass
            if type(val) == GameActivity:
                pass # do something
            else:
                await g.ainit()
                PLAYTIME_SESSIONS[self.u.user.id]['sessions'][activity['app'].id] = g
            
            
            
    
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
                pass # stop
                continue
            
            if b_activity is not None and a_activity is not None:
                print("**ACTIVITY HEARTBEAT**")
                if b_activity['app'] == a_activity['app']:
                    pass # update 'last_refresh' if tracking
                    continue
                
                else:
                    pass # stop b_activity and start a_activity. Activity has changed
                
                
        
        
        
        
        
        
        
        
        
        
        # # A change in games playing detected
        # #
        # # START check
        # if len(self.b['playing']) < len(self.a['playing']):
        #     print("**STARTED PLAYING**")
        #     for b_activity, a_activity in itertools.zip_longest(self.b['playing'], self.a['playing']):
                
        #         # Before will be none in this case if the user has
        #         # started playing game (multiple activity support)
        #         if b_activity is not None:
        #             if b_activity['app'].id != a_activity['app'].id:
        #                 pass
        #                 '''Create new playtime entry for selected activity'''
        #         else:
        #             pass
        #             '''Create new playtime entry'''
        # elif len(self.b['playing']) > len(self.a['playing']):
        #     print("**STOPPED PLAYING**")
        
        # # Activity Heartbeat / No activity
        # else:
        #     print("**ACTIVITY HEARTBEAT**")
        #     for b_activity, a_activity in itertools.zip_longest(self.b['playing'], self.a['playing']):
                
        #         # If activity is same, update 'last_heartbeat' in
        #         # PLAYTIME_ENTRIES object
        #         if b_activity is not None and a_activity is not None:
        #             pass
        #             '''Update 'last_heartbeat' in GameActivity object'''
                
    
    
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
    
    