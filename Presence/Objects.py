import discord
import itertools
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
        
    
    def __sort_key(self, v) -> str:
        return v.name
    
    # Sort all user activities into dicts
    # that identify their type.
    #
    # Other activity types would be added
    # here to be sorted.
    def __sort_activities(self) -> None:
        
        # i = 0
        # while True:
        #     b_act = {'act': self.b['user'].activities[i], 'is_playing': False}
        #     a_act = {'act': self.a['user'].activities[i], 'is_playing': False}
            
        #     try:
        #         if b_act['act'] is discord.ActivityType.playing:
        #             self.b['playing'].append({
        #                     'activity': b_act['act'],
        #                     'name': b_act['act'].name,
        #                     'app': None
        #                 })
        #     except: self.b['playing'].append(None)
        
        '''
        The purpose of creating two new activity lists here is so
        we can ...
        '''
        
        # b_activities = []
        # a_activities = []
        # for b_activity, a_activity in itertools.zip_longest(self.b['user'].activities, self.a['user'].activities):
            
        #     # Create a list we can sort by name. If activity does not have
        #     # name attribute, do not add to list.
            
        #     if b_activity is not None:
        #         try:
        #             b_activity.name
        #             b_activities.append(b_activity)
        #         except: pass
                
        #     if a_activity is not None:
        #         try:
        #             a_activity.name
        #             a_activities.append(a_activity)
        #         except: pass
        
        # b_activities.sort(key=self.__sort_key)
        # a_activities.sort(key=self.__sort_key)
        
        
        
        i = 0
        for b_activity, a_activity in itertools.zip_longest(self.b['user'].activities, self.a['user'].activities):
            b_activity: discord.Activity
            a_activity: discord.Activity
            print(
                f"b_act {b_activity}\n"
                f"a_act {a_activity}"
            )
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

            # if self.b['playing'][i] is None and self.a['playing'][i] is None:
            
            # i += 1
            
            # if 
        
        
        print("sorting, maybe")
        # array1 = self.b['playing']
        # array2 = self.a['playing']
        
        # for i in range(len(array1)):
        #     for j in range(len(array2)):
        #         if array1[i] and array2[j] and array1[i]['name'] == array2[j]['name']:
        #             array2[i], array2[j] = array2[j], array2[i]
        # print(array1, "\n\n", array2)
        
        for i in range(len(self.b['playing'])):
            for j in range(len(self.a['playing'])):
                if self.b['playing'][i] and self.a['playing'][j] and \
                    self.b['playing'][i]['name'] == self.a['playing'][j]['name']:
                        self.a['playing'][i], self.a['playing'][j] = self.a['playing'][j], self.a['playing'][i]
        print("sorted!")
        
        '''Needs to be sorted ^^^^'''
        
        print(
            "shit n stuf:\n"
            f"b activities len {len(self.b['user'].activities)}\n"
            f"a activities len {len(self.a['user'].activities)}\n"
            f"b playing len {len(self.b['playing'])}\n"
            f"a playing len {len(self.a['playing'])}\n"
            f"{self.b['playing']}\n\n"
            f"{self.a['playing']}\n"
        )
        
        
        # for user in [self.b, self.a]:
        #     for activity in user['user'].activities:
        #         activity: discord.Activity
        #         try:
        #             if activity.type is discord.ActivityType.playing:
                        
        #                 # Try-except is here because if we cannot get an activity
        #                 # name, then there is no entry in the database anyway.
        #                 # Skip activity.
        #                 try:
        #                     user['playing'].append({
        #                         'activity': activity,
        #                         'name': activity.name,
        #                         'app': None
        #                     })
        #                 except: continue
        #         except: pass
        #     user['playing'].sort(key=self.__sort_key)
        
        '''
        B:
            [Activity 1: VSCode]
        
        A:
            [Activity 1: Minecraft]
            [Activity 2: VSCode]
            
        b1 != a1
        '''
    
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
        #         print(f"{i+1}. {a['app']}")
        # print('\n\n')
        
    
    
    async def __determine_status(self) -> None:
        global PLAYTIME_SESSIONS
        
        
        for b_activity, a_activity in itertools.zip_longest(self.b['playing'], self.a['playing']):
            
            # If not playing
            if b_activity is None: pass
                
        
        
        
        
        
        
        
        
        
        
        # A change in games playing detected
        #
        # START check
        if len(self.b['playing']) < len(self.a['playing']):
            print("**STARTED PLAYING**")
            for b_activity, a_activity in itertools.zip_longest(self.b['playing'], self.a['playing']):
                
                # Before will be none in this case if the user has
                # started playing game (multiple activity support)
                if b_activity is not None:
                    if b_activity['app'].id != a_activity['app'].id:
                        pass
                        '''Create new playtime entry for selected activity'''
                else:
                    pass
                    '''Create new playtime entry'''
        elif len(self.b['playing']) > len(self.a['playing']):
            print("**STOPPED PLAYING**")
        
        # Activity Heartbeat / No activity
        else:
            print("**ACTIVITY HEARTBEAT**")
            for b_activity, a_activity in itertools.zip_longest(self.b['playing'], self.a['playing']):
                
                # If activity is same, update 'last_heartbeat' in
                # PLAYTIME_ENTRIES object
                if b_activity is not None and a_activity is not None:
                    '''Update 'last_heartbeat' in GameActivity object'''
                
    
    
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
    
    