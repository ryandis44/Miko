'''
Respond with a simple help message whenever Miko is mentioned
'''



from Database.MikoCore import MikoCore

async def increment_guild_message_count(mc: MikoCore) -> None:
    if mc.profile.feature_enabled('INCREMENT_GUILD_MESSAGE_COUNT') != 1: return
    await mc.guild.increment_message_count()