#from utils.playtime import playtime_interrupt
from select import select
import time
from Database.database_class import Database
from Playtime.playtime import sessions_hash_table
from Voice.VoiceActivity import VOICE_SESSIONS

hi = Database("HandleInterrupt.py")

def interrupt() -> None:
    current_time = int(time.time())
    
    upd_cmd = (
        f"UPDATE PERSISTENT_VALUES SET value='{current_time}' "
        f"WHERE variable='GLOBAL_REBOOT_TIME_ACTIVITY'"
    )
    hi.db_executor(upd_cmd)
    
    print("\n[1/2] Ending active playtime sessions...")
    sc = 0
    for pair in sessions_hash_table.get_all:
        pair[0][1].close_activity_entry(True, current_time=current_time)
        sc += 1
        print(f"> Ended {pair[0][1].get_user}'s playtime session.")
    print(f"[1/2] Ended {sc} playtime sessions.")

    print("\n[2/2] Ending active voice sessions...")
    vsc = 0
    for key, sesh in VOICE_SESSIONS.items():
        sesh.end(current_time)
        vsc += 1
        print(f"> Ended {sesh.member}'s voice session.")
    print(f"[2/2] Ended {vsc} voice sessions.")

    print("All active sessions have ended.\n")
    return

def nullify_restore_time() -> None:
    upd_cmd = (
        "UPDATE PERSISTENT_VALUES SET value=NULL "
        "WHERE variable='GLOBAL_REBOOT_TIME_ACTIVITY'"
    )
    hi.db_executor(upd_cmd)
    return