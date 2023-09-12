import discord
import datetime
import time

DISCONNECT_ENTRIES = {discord.Guild.id: dict[discord.Member.id: discord.AuditLogEntry]}

async def auditEntry(entry: discord.AuditLogEntry):
    if entry.user.id != 1017998983886545068: return
    if entry.action == discord.AuditLogAction.member_disconnect:
        # if entry.user_id == 357939301100683276:
            print("Disconnect found")
            
            provision_hash_table(entry)
            
            # await entry.user.timeout(
            #     datetime.datetime.now().astimezone() + datetime.timedelta(minutes=1)
            # )


def provision_hash_table(entry: discord.AuditLogEntry):
    
    if DISCONNECT_ENTRIES.get(entry.guild.id) is not None:
        cached_entry: discord.AuditLogEntry = DISCONNECT_ENTRIES[entry.guild.id].get(entry.user.id)
        if cached_entry is not None and cached_entry.created_at >= entry.created_at: return # if we have a newer entry, discard the older one 
    
    if DISCONNECT_ENTRIES.get(entry.guild.id) is None:
        DISCONNECT_ENTRIES[entry.guild.id] = {entry.user_id: entry}
    else:
        DISCONNECT_ENTRIES[entry.guild.id][entry.user_id] = entry


async def handle_disconnect(guild: discord.Guild):
    print("Handling disconnect")
    
    async for entry in guild.audit_logs(action=discord.AuditLogAction.member_disconnect, limit=10):
        # print(entry.user.name)
        try:
            cached_entry: discord.AuditLogEntry = DISCONNECT_ENTRIES[entry.guild.id][entry.user_id]
        except:
            provision_hash_table(entry)
            continue
            
        if cached_entry.extra != entry.extra:
            provision_hash_table(entry)
            print(f"Entry diff detected: {entry.user.name}")
        