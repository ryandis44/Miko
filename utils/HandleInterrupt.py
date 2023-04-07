#from utils.playtime import playtime_interrupt
from select import select
import time
from Database.database_class import Database
from Presence.Objects import PLAYTIME_SESSIONS
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
    playtime_sessions = 0
    users = PLAYTIME_SESSIONS.items()
    for user_sessions in users:
        for s in user_sessions[1]['sessions']:
            # 1 is the value of the key value pair of the dict containing all sessions for this user
            # 'sessions' denotes we want sessions
            # 's' is the individual session
            game = user_sessions[1]['sessions'][s]
            game.close_activity_entry_synchronous(current_time=current_time, keep_sid=True)
            playtime_sessions += 1
            print(f"> Ended {game.u.user}'s playtime session.")
    print(f"[1/2] Ended {playtime_sessions} playtime sessions.")

    print("\n[2/2] Ending active voice sessions...")
    voicetime_sessions = 0
    for key, sesh in VOICE_SESSIONS.items():
        sesh.close_voice_entry_synchronous(current_time)
        voicetime_sessions += 1
        print(f"> Ended {sesh.member}'s voice session.")
    print(f"[2/2] Ended {voicetime_sessions} voice sessions.")

    print("All active sessions have ended.\n")
    return

def nullify_restore_time() -> None:
    upd_cmd = (
        "UPDATE PERSISTENT_VALUES SET value=NULL "
        "WHERE variable='GLOBAL_REBOOT_TIME_ACTIVITY'"
    )
    hi.db_executor(upd_cmd)
    return