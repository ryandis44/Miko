import re
import math

def parse_inventory(inventory, message):
    pattern_count = r'.*?\*\*(.*)\*\*.*' 
    pattern_dust = r'.*?\`(.*)\`.*'
    match_count = re.findall(pattern_count, inventory)
    match_dust = re.findall(pattern_dust, inventory)

    d2 = [954585066619682906, 903469976759959613] # wild, asta
    d3 = [747498003601817781, 511312859523973140, 957484905590325281] # luffy, sasuke, yumeko
    d4 = 981078995539988500 # eri

    divisor = 1
    if message.author.id in d2: divisor = 2
    elif message.author.id in d3: divisor = 3
    elif message.author.id == d4: divisor = 4

    match_count = [str(x).replace(',', '') for x in match_count]

    match_count = list(map(int, match_count)) #convert list to int
    match_count[:] = [math.floor(x / divisor) for x in match_count] #divide each element by 2
    match_count = [str(x) for x in match_count] #convert list to string

    temp = []
    for i in range(len(match_count)):
        temp.append(match_count[i]+" ")
        if i == (len(match_count) - 1):
            temp.append(match_dust[i]+"")
        else:
            temp.append(match_dust[i]+", ")

    return f"`{''.join(temp)}`"

def check_for_karuta(author):
    def inner_check(message):
        return message.author.id == author
    return inner_check