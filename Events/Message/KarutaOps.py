'''
Respond with a simple help message whenever Miko is mentioned
'''



import re

from Database.MikoCore import MikoCore

async def karuta_ops(mc: MikoCore) -> None:
    # if the feature is enabled in this guild and the user is not a bot unless the user is Karuta
    if mc.profile.feature_enabled('KARUTA_OPS') != 1 or (mc.user.user.bot and mc.user.user.id != 646937666251915264) or mc.channel.channel_settings['karuta_ops'] not in ['ALL', 'VISUAL']: return
    
    match mc.channel.channel_settings['karuta_ops']:
        case 'ALL':
            
            if re.match(r"^k.*$", mc.message.message.content.lower()):
                await mc.message.message.delete()
                return
            
        case 'VISUAL':
            for command in mc.tunables('KARUTA_COMMANDS_TO_DELETE').split(','):
                if re.match(rf"^k{command}.*$", mc.message.message.content.lower()) or command == mc.message.message.content.lower():
                    await mc.message.message.delete()
                    break