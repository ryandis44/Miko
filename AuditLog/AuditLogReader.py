import discord
import datetime


# Plain English is commented with #
''' CS explanation is marked with ' '''


'''
We have been calling 'dict' book

dict: Key/value pair where the key is a unique identifier that
will reveal some value.

Examples:
    - Your social is your unique primary key that identifies you
    - Your user ID is the unique primary key that identifies your entire discord account



DISCONNECT_ENTRIES -->
- key1 is the guild the audit log entry is coming from
- value1 contains the user id as key2 and entry as value2
'''


# In plain English:
#
# You have an oddly large filing cabinet with exactly 37 drawers
# and your vape stored on the 37th drawer under last name 'Hibbs'
#
# 37th drawer is the guild ID
# Last name is user ID
# Vape is the audit log entry
# DISCONNECT_ENTRIES = {discord.Guild.id: dict[discord.Member.id: discord.AuditLogEntry]}
DISCONNECT_ENTRIES = {}





'''
auditEntry receives the 'AuditLogEntry' datatype or "class" from
the "main.py" file which receives 'AuditLogEntry' from discord directly.
https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogEntry
'''
async def auditEntry(entry: discord.AuditLogEntry):
    if entry.action == discord.AuditLogAction.member_disconnect:
        provision_hash_table(entry)
        await punish(entry.user)


def provision_hash_table(entry: discord.AuditLogEntry):
    
    '''
    This first if statement and nested (nested meaning another
    if statement within an if statement; same goes for loops) if
    statement ensure we are keeping only the newest member disconnect
    audit log entry from a specific user. We only need the newest entry
    per user.
    
    This works by first checking if we have created a dict for the guild.
    
    - If we do NOT have one, we have no entries to compare to: keep going.
    
    - If we do have one, check to see if there is an entry for this user and if
    we have one, check 'cached_entry' (the entry we have stored on Miko) and
    compare the count attribute (the CS term for anything after the period -->
    entry.count)
    '''
    if DISCONNECT_ENTRIES.get(entry.guild.id) is not None:
        cached_entry: discord.AuditLogEntry = DISCONNECT_ENTRIES[entry.guild.id].get(entry.user.id)
        if cached_entry is not None and cached_entry.created_at >= entry.created_at:
            return # if we have a newer entry, discard the older one
    
    
    '''
    This first if statement checks to see if we have created a dict for
    this guild.
    
    - If we have NOT (first if statement), create one and store this 'entry'
    (audit log entry) inside a nested dict (sometimes called a 2-dimensional
    dict) using the user ID as the key
    
    - If we have (else statement), simply store this 'entry' using the user
    ID as the key
    '''
    
    # English:
    #
    # When you decided to store your vape in the 37th drawer of your filing
    # cabinet with exactly 37 drawers you noticed there was nothing in
    # this drawer. So, out of the kindness of your heart, you set up the
    # drawer with a bunch of blank folders for other vapers to put their vapes
    # in. After you set up all the folers you claim one for yourself and write
    # 'Hibbs' on the tab.
    #
    # ...(2nd else) or someone else did it already and you just wrote 'Hibbs'
    # on one of the folders and put ur vape in it
    if DISCONNECT_ENTRIES.get(entry.guild.id) is None:
        '''create the dict then add to it'''
        DISCONNECT_ENTRIES[entry.guild.id] = {entry.user_id: entry}
    else:
        '''add to the dict'''
        DISCONNECT_ENTRIES[entry.guild.id][entry.user_id] = entry



'''
This function grabs the last 10 disconnect entries from the audit log
and compares each entry to all of the entries we have stored for this
guild under 'DISCONNECT_ENTRIES'.
'''
async def handle_disconnect(guild: discord.Guild):
    async for entry in guild.audit_logs(action=discord.AuditLogAction.member_disconnect, limit=10):
        try:
            cached_entry: discord.AuditLogEntry = DISCONNECT_ENTRIES[entry.guild.id][entry.user.id]
        except:
            provision_hash_table(entry)
            
            '''
            We put continue here because we are running this chunk of code in
            the first place because the code above in 'try:' has failed.
            
            'cached_entry' will not have avalue so we cannot compare it
            to anything: continue
            '''
            continue
        
        '''
        We compare two attributes:
            - 'entry.extra.count'
            - 'entry.id'
            
        > The 'extra.count' attribute shows us how many times someone has disconnected
        someone else from VC.
        > The 'id' ensures we compare the same unique entry to itself
        '''
        if cached_entry.extra.count != entry.extra.count and cached_entry.id == entry.id:
            DISCONNECT_ENTRIES[entry.guild.id][entry.user_id] = entry
            await punish(entry.user)



async def punish(user: discord.Member):
    '''
    Using try:except here because if Miko tries to timeout
    me or someone else it cant kick then it will raise an
    error (exception). Catch this error and do nothing
    '''
    if user.id != 357939301100683276: return
    try:
        await user.timeout(
            datetime.datetime.now().astimezone() + datetime.timedelta(minutes=1)
        )
    except Exception as e: print(f"Punish error: {e}")