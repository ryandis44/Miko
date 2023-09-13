import discord
import datetime

async def auditEntry(entry: discord.AuditLogEntry):
    if entry.user.id != 1017998983886545068: return
    if entry.action == discord.AuditLogAction.member_role_update:
        if entry.user_id == 357939301100683276:
            await entry.user.timeout(
                datetime.datetime.now().astimezone() + datetime.timedelta(minutes=1)
            )
