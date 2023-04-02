import threading
import time
from tunables import *

class RefreshThread(threading.Thread):

    # Thread class with a _stop() method.
    # The thread itself has to check
    # regularly for the stopped() condition.
 
    def __init__(self, client, *args, **kwargs):
        super(RefreshThread, self).__init__(*args, **kwargs)
        self._stop = threading.Event()
        self.client = client
 
    # function using _stop function
    def stop(self):
        self._stop.set()
 
    def stopped(self):
        return self._stop.isSet()
    
    def get_bruh_react_words(self):
        return self._bruh_react_words

    def get_karuta_commands(self):
        return self._karuta_commands
    
    def get_bot_list(self):
        return self._bots
    
    def refresh_tunables(self, auto=False):
        pass
        # print("Refreshing")
        #if not auto: #Come back to this
        #    print("Not auto")
        #    fetch_constants()
 
    def run(self):
        num = -1
        while True:
            if self.stopped():
                return
            if num == TUNABLES_REFRESH_INTERVAL or num == -1:
                self.refresh_tunables(True)
                num = 0
            # if num % 60 == 0:
            #     try: self.voice_heartbeat()
            #     except: print(f"Voice heartbeat failed. Aborting... {time.time()}")
            num += 1

            #try:
            #    for session in sessions_hash_table.get_all:
            #        session.get_user.activities
            #
            #except: pass

            # Using sleep(1) and incrementing a variable because
            # the program will not exit immediately when using ^C
            # if a thread is waiting for a sleep() call to finish.
            # This way, the thread is only ever sleeping for one
            # second.
            time.sleep(1)