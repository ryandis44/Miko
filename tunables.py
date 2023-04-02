from discord import Color
from discord import ButtonStyle, SelectOption
from json import loads
from Database.database_class import Database, AsyncDatabase
from utils.HashTable import HashTable
db = AsyncDatabase("tunables.py")

GENERIC_CONFIRM_STYLE=ButtonStyle.green
GENERIC_DECLINE_STYLE=ButtonStyle.red
GREEN_BOOK_SUCCESS_COLOR=0x00FF00
GREEN_BOOK_NEUTRAL_COLOR=0xFFFFFF
GREEN_BOOK_WARN_COLOR=0xFFFF00
GREEN_BOOK_FAIL_COLOR=0xFF0000
GLOBAL_EMBED_COLOR=Color.magenta()
PLEX_EMBED_COLOR=0xE5A00D
TUNABLES_REFRESH_INTERVAL=300

TUNABLES = {}
def tunables(s):
    try: return TUNABLES[s]
    except Exception as e:
        print(f"TUNABLES ERROR: Could not find '{s}' | {e}")
        return None

def all_tunable_keys() -> list: return [*TUNABLES]

def tunables_init(): # Initial call cannot be async
    assign_tunables(
        val=Database("TUNABLES INITIALIZATION").db_executor(
            "SELECT * FROM TUNABLES "
            "ORDER BY variable ASC"
        )
    )

async def tunables_refresh():
    assign_tunables(await db.execute(
        "SELECT * FROM TUNABLES "
        "ORDER BY variable ASC"
    ))

def assign_tunables(val):
    global TUNABLES
    TUNABLES = {}
    for tunable in val:
        if tunable[1] == "TRUE": TUNABLES[tunable[0]] = True
        if tunable[1] == "FALSE": TUNABLES[tunable[0]] = False
        elif tunable[1] not in ["TRUE", "FALSE"]:
            if tunable[1] is not None and tunable[1].isdigit(): TUNABLES[tunable[0]] = int(tunable[1])
            else: TUNABLES[tunable[0]] = tunable[1]
    configure_tunables()

def configure_tunables() -> None:
    global TUNABLES
    TUNABLES['OPENAI_PERSONALITIES'] = []
    temp = []
    for key, val in TUNABLES.items():
        if 'GUILD_PROFILE_' in key:
            TUNABLES[key] = GuildProfile(profile=str(key)[14:])
        
        if 'OPENAI_PERSONALITY_' in key:
            d = loads(val)
            temp.append(d)
            
    
    def srt(d) -> int:
        return d['position']
    temp.sort(key=srt)
    for d in temp:
        TUNABLES['OPENAI_PERSONALITIES'].append(
            SelectOption(
                label=d['label'],
                description=d['description'],
                value=d['value'],
                emoji=d['emoji']
            )
        )
        TUNABLES[f"OPENAI_PERSONALITY_{d['value']}"] = d['prompt']





class GuildProfile():

    def __init__(self, profile: str):
        self.params = str(tunables(f'GUILD_PROFILE_{profile}')).split(',')
        self.profile = profile
        self.v = {}
        
        self.__commands = {'all_enabled': False, 'inverse': False}
        self.__features = {'all_enabled': False, 'inverse': False}
        self.__handle_params()

    def __str__(self):
        return self.params
    
    def __handle_params(self) -> None:
        for option in self.params:
            option = option.split("[")
            option[1] = option[1].replace("]", "")
            
            if option[0].startswith("!"):
                option[0] = option[0].replace("!", "")
                inverse = True
            else: inverse = False
            
            match option[0]:
                
                case "COMMANDS":
                    self.__commands['inverse'] = inverse
                    if option[1] in ["ALL"]:
                        self.__commands['all_enabled'] = True
                        continue
                    prefix = "C"
                    
                case "FEATURES":
                    self.__features['inverse'] = inverse
                    if option[1] in ["ALL"]:
                        self.__features['all_enabled'] = True
                        continue
                    prefix = "F"
                
                case _: prefix = None


            option = str(option[1]).split(";")
            for cmd in option:
                self.v[f'{prefix}_{cmd.upper()}'] = not inverse
            
    
    # For the following two functions, return values mean:
    # - 0: Guild profile does not have command enabled
    # - 1: Guild profile and tunables have command enabled
    # - 2: Tunables does not have command enabled
    
    def cmd_enabled(self, cmd: str) -> int:
        if not tunables(f'COMMAND_ENABLED_{cmd.upper()}'): return 2
        if self.__commands['all_enabled']:
            if self.__commands['inverse']: return 0
            return 1
        
        try: val = self.v[f"C_{cmd}"]
        except: val = None
        if val is None: val = self.__commands['inverse']
        return 1 if val else 0
    
    def feature_enabled(self, f: str) -> int:
        if not tunables(f'FEATURE_ENABLED_{f.upper()}'): return 2
        if self.__features['all_enabled']:
            if self.__features['inverse']: return 0
            return 1
        
        try: val = self.v[f"F_{f}"]
        except: val = None
        if val is None: val = self.__features['inverse']
        return 1 if val else 0