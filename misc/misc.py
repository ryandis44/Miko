import random
import discord
import itertools
from datetime import date, datetime


def equal_tuples(tuple1, tuple2) -> bool:
    if len(tuple1) != len(tuple2):
        print("LENGTH IS NOT EQUAL")
        return False
    
    for i1, i2 in zip(tuple1, tuple2):
        if repr(i1) != repr(i2):
            # print(f"{i1} DOES NOT EQUAL {i2}")
            return False
    return True

# Returns a user ID without <@> i.e. <@221438665749037056> --> 221438665749037056
def translate_mention(uid):
    temp = uid.translate({ ord(c): None for c in "<@>" })
    return temp

async def get_user_object(self, ctx, uid):

    # Get user mentioned
    temp = translate_mention(uid)
    
    try:
        user = ctx.guild.get_member(int(temp))
        if user is None:
            user = await self.client.fetch_user(int(temp))
    except: user = None
    
    return user
    

# Formats large numbers into a more compact, human readible
# format: 149,237 —> 149.2K
def human_format(num):
    if num > 999: modify = True
    else: modify = False
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    # add more suffixes if you need them
    if modify:
        return '%.1f%s' % (num, ['', 'K', 'M', 'B', 'T', 'P'][magnitude])
    else:
        return num

def percentage_two_decimals(var1, var2):
    return str('{:.2f}'.format(round(var1 / var2 * 100, 2)))

def react_all_emoji_list():
    return ['<:angry:947693801009459200>', '<:4k:947696286457536512>', '<:blushass:947694381337571400>', '<:RAGE:947694105159421982>', '<:ZAMN:947693063915061308>',
            '<:bitch:1008993470364528690>', '<:hector_talking:947690384841146368>', '<a:SussySebas:914318423889154058>', '<:huh:947699016542584842>', '<:hmmmgay:947696715136376832>',
            '<:okand:947697439048073276>', '<:shocked:947697022914416680>', '<:kektor:912135024470552657>', '<a:animatedBoost:947695625934356610>', '<a:godhelpus:903162947260547082>',
            '<:sus:947692719378161704>', '<:wideshelby:959490142412894318>', '<:pepeNoU:947702070088196156>', '<:pepeFat:947700271478349825>']

def time_elapsed(seconds, format):
    secs = seconds
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
      
    match format:
        case ":":
            return "%d:%02d:%02d" % (hours, minutes, seconds)
        case "h":
            temp = []
            
            d = False
            h = False
            if days > 0:
                temp.append(f"{days}d ")
                d = True
            if hours > 0 or d is True:
                temp.append(f"{hours}h ")
                h = True
            if minutes > 0 or h is True:
                temp.append(f"{minutes}m ")
            temp.append(f"{seconds}s")
            return ''.join(temp)
        
        case "r":
            return (secs / 60) / 60
            

def generate_nickname(message: discord.Message):
    if message.content == "": return f"{message.author.name}"
    letters = 0
    for word in message.content.split():
        letters += len(word)
    
    if letters <= 10: return f"{message.content}"
    
    i = 0
    message = message.content.split()
    while True:
        word1 = message[random.randint(0, (len(message) - 1))]
        word2 = message[random.randint(0, (len(message) - 1))]
        if len(word1) + len(word2) <= 31: break
        if i >= 10: break
        i += 1
    return f"{word1} {word2}"

def sanitize_track_name(track):
    name = track.title.translate({ ord(c): None for c in "[]*_" })
    return name

def today():
    return int(datetime.combine(date.today(), datetime.min.time()).timestamp())

# Searches up to "'Key' Slot[0-4]" to allow duplicate keys with same id
# To use this function, the object must have a 'comparable' property that
# can be used to identify itself amongst other objects within this hash table
def locate_htable_obj(map: dict, key, comparable=None) -> list:
    i = 0
    while True:
        ref_key = f"{key} Slot{i}"
        try: val = map[ref_key]
        except: val = None
        if val is not None:
            if comparable is not None and val.comparable == comparable: return [val, ref_key]
            elif comparable is None: return [val, None]
        if i >= 4: return [None, None]
        i += 1

def determine_htable_key(map: dict, key):
    i = 0
    while True:
        new_key = f"{key} Slot{i}"
        try: val = map[new_key]
        except: val = None
        if val is None: return new_key
        if i >= 4: return None
        i += 1

def emojis_1to10(i):
    emojis = [
            "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣",
            "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"
        ]
    return emojis[i]