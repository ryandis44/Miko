import discord
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
        await self.__playing_init()
        
    
    # Sort all user activities into dicts
    # that identify their type.
    #
    # Other activity types would be added
    # here to be sorted.
    def __sort_activities(self) -> None:
        for user in [self.b, self.a]:
            for activity in user['user'].activities:
                activity: discord.Activity
                try:
                    if activity.type is discord.ActivityType.playing:
                        user['playing'].append({
                            'activity': activity,
                            'app': None
                        })
                except: pass
    
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
    
    '''
    async def __playing_init(self) -> None:
        await self.__get_activity_attributes() # 1.
        await self.__determine_status() # 2. and 3.
    
    
    async def __determine_status(self) -> None:
        global PLAYTIME_SESSIONS
        
        # A change in games playing detected
        #
        # START check
        if self.b['playing'] != self.a['playing']:
            if len(self.b['playing']) < len(self.a['playing']):
                
    
    
    # Get application ID, session ID, start time, and
    # activity name, if applicable
    async def __get_activity_attributes(self) -> None:
        for user in [self.b, self.a]:
            for app in user['playing']:
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