import discord
import datetime
import time


'''
DISCONNECT_ENTRIES -->
- key1 is the guild the audit log entry is coming from
- value1 contains the user id as key2 and entry as value2
'''


DISCONNECT_ENTRIES = {discord.Guild.id: dict[discord.Member.id: discord.AuditLogEntry]}

async def auditEntry(entry: discord.AuditLogEntry):
    if entry.action == discord.AuditLogAction.member_disconnect:
            provision_hash_table(entry)


def provision_hash_table(entry: discord.AuditLogEntry):
    
    if DISCONNECT_ENTRIES.get(entry.guild.id) is not None:
        cached_entry: discord.AuditLogEntry = DISCONNECT_ENTRIES[entry.guild.id].get(entry.user.id)
        if cached_entry is not None and cached_entry.created_at >= entry.created_at:
            return # if we have a newer entry, discard the older one
    
    if DISCONNECT_ENTRIES.get(entry.guild.id) is None:
        # create the list then add to it
        DISCONNECT_ENTRIES[entry.guild.id] = {entry.user_id: entry}
    else:
        # add to the list
        DISCONNECT_ENTRIES[entry.guild.id][entry.user_id] = entry


async def handle_disconnect(guild: discord.Guild):
    async for entry in guild.audit_logs(action=discord.AuditLogAction.member_disconnect, limit=10):
        try:
            cached_entry: discord.AuditLogEntry = DISCONNECT_ENTRIES[entry.guild.id][entry.user.id]
        except:
            provision_hash_table(entry)
            continue
        
        
        if cached_entry.extra.count != entry.extra.count and cached_entry.created_at == entry.created_at:
            DISCONNECT_ENTRIES[entry.guild.id][entry.user_id] = entry
            
            await entry.user.timeout(
                datetime.datetime.now().astimezone() + datetime.timedelta(minutes=1)
            )