from discord import Color
from discord import ButtonStyle
from Database.database_class import Database
from utils.HashTable import HashTable
gc = Database("tunables.py")

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

def fetch_tunables():

    val = gc.db_executor(exec_cmd="SELECT * FROM TUNABLES")
    global TUNABLES
    for tunable in val:
        if tunable[1] == "TRUE": TUNABLES[tunable[0]] = True
        if tunable[1] == "FALSE": TUNABLES[tunable[0]] = False
        elif tunable[1] not in ["TRUE", "FALSE"]:
            if tunable[1] is not None and tunable[1].isdigit(): TUNABLES[tunable[0]] = int(tunable[1])
            else: TUNABLES[tunable[0]] = tunable[1]
    
    for key, val in TUNABLES.items():
        if 'GUILD_PROFILE_' in key:
            TUNABLES[key] = GuildProfile(profile=str(key)[14:])





class GuildProfile():

    def __init__(self, profile: str):
        self.params = str(tunables(f'GUILD_PROFILE_{profile}')).split(',')
        self.profile = profile
        self.vals = HashTable(1_000)
        # self.vals = {}
        
        self.__commands = {'all_enabled': False, 'inverse': False}
        self.__features = {'all_enabled': False, 'inverse': False}
        self.__handle_params()

    def __str__(self):
        return f"{self.profile} GuildProfile Object"
    
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
                self.vals.set_val(
                    key=f"{prefix}_{cmd.upper()}",
                    val=not inverse
                )
            
    
    def cmd_enabled(self, cmd: str) -> bool:
        if self.__commands['all_enabled']:
            if self.__commands['inverse']: return False
            return True
        
        val = self.vals.get_val(f"C_{cmd}")
        if val is None: val = self.__commands['inverse']
        return val
    
    def feature_enabled(self, f: str) -> bool:
        if self.__features['all_enabled']:
            if self.__features['inverse']: return False
            return True
        
        val = self.vals.get_val(f"F_{f}")
        if val is None: val = self.__features['inverse']
        return val