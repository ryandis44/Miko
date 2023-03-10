
import asyncio
import time
import threading
from Database.GuildObjects import MikoMessage
from tunables import *

class RefreshThread(threading.Thread):

    # Thread class with a _stop() method.
    # The thread itself has to check
    # regularly for the stopped() condition.
 
    def __init__(self, mm: MikoMessage, *args, **kwargs):
        super(RefreshThread, self).__init__(*args, **kwargs)
        self._stop = threading.Event()
        self.mm = mm
 
    # function using _stop function
    def stop(self):
        self._stop.set()
 
    def stopped(self):
        return self._stop.isSet()
 
    def run(self):
        num = -1
        while True:
            if self.stopped(): return
            
            
            
            
            
            num += 1
            time.sleep(1)
            

async def thread_test(mm: MikoMessage) -> None:
    
    msg = await mm.message.reply(
        content=tunables('LOADING_EMOJI')
    )
    
    await asyncio.sleep(5)
    
    await msg.edit(
        content="Complete"
    )