import discord
import collections
from discord.utils import get
from tunables import *

def get_holiday(ctx, info_to_return):
    holiday1 = get(ctx.guild.roles, id=895834307338326057)
    holiday2 = get(ctx.guild.roles, id=895834403190759454)
    holiday3 = get(ctx.guild.roles, id=895834443460280360)
    holiday4 = get(ctx.guild.roles, id=895834487479476294)

    member_counts = [len(holiday1.members), len(holiday2.members), len(holiday3.members), len(holiday4.members)]

    next_role = 0
    
    lowest = member_counts[0]
    for i, member_count in enumerate(member_counts):
        if member_count < lowest:
            lowest = member_count
            next_role = i

    if info_to_return == "EMBED":

        complete_holiday_members = holiday1.members + holiday2.members + holiday3.members + holiday4.members
        all_members = ctx.guild.members

        # For determining the contents of our embed description
        temp = []
        temp.append(f"{holiday1.mention} has `{str(member_counts[0])}` members\n")
        temp.append(f"{holiday2.mention} has `{str(member_counts[1])}` members\n")
        temp.append(f"{holiday3.mention} has `{str(member_counts[2])}` members\n")
        temp.append(f"{holiday4.mention} has `{str(member_counts[3])}` members\n\n")
        temp.append("Total members assigned\n a holiday role: `")
        # Using set here because we want to know how many members are assigned
        # a holiday role without including members assigned multiple
        # holiday roles.
        temp.append(f"{str((len(set(complete_holiday_members))))}` `({str(len(all_members))})`\n\n")

        # For determining members that are not
        # assigned to any holiday role
        unassigned_members = [x for x in all_members if x not in complete_holiday_members]

        if len(unassigned_members) == 0:
            temp.append("All members are assigned\na holiday role.")
        else:
            temp.append(f"`{str(len(unassigned_members))}` ")
            if len(unassigned_members) == 1: temp.append("member")
            else: temp.append("members")
            temp.append(" __not__ assigned\na holiday role:\n")

            list_iterator = 0
            for member in unassigned_members:
                if list_iterator % 3 == 0 and list_iterator != 0:
                    temp.append("\n")
                if list_iterator == (len(unassigned_members) - 1):
                    temp.append(str(member.mention))
                else:
                    temp.append(str(member.mention) + ", ")
                    list_iterator += 1


        # If our 'raw' list is the same length as our list
        # as a set, then we do not have any duplicates and
        # can move on. Otherwise, put all duplicates into
        # a list and append to our 'temp' list.
        temp.append("\n\n")
        if len(complete_holiday_members) == len(set(complete_holiday_members)):
            temp.append("There are no members with\nmultiple holiday roles.")
        else:
            members_duplicate_roles = [item for item, count in collections.Counter(complete_holiday_members).items() if count > 1]
            temp.append(f"`{len(members_duplicate_roles)}` ")
            if len(members_duplicate_roles) == 1: temp.append("member is")
            else: temp.append("members are")
            temp.append(" assigned\n__multiple__ holiday roles:\n")

            list_iterator = 0
            for member in members_duplicate_roles:
                if list_iterator % 3 == 0 and list_iterator != 0:
                    temp.append("\n")
                if list_iterator == (len(members_duplicate_roles) - 1):
                    temp.append(str(member.mention))
                else:
                    temp.append(str(member.mention) + ", ")
                    list_iterator += 1


        # For determining our embed footer
        temp2 = []
        temp2.append("Next role to assign: ")

        match next_role:
            case 0: temp2.append(holiday1.name)
            case 1: temp2.append(holiday2.name)
            case 2: temp2.append(holiday3.name)
            case 3: temp2.append(holiday4.name)

        embed = discord.Embed (
            title = 'Holiday Role Assignment',
            color = GLOBAL_EMBED_COLOR,
            description=f"{''.join(temp)}"
        )
        embed.set_footer(text=f"{''.join(temp2)}")
        embed.set_thumbnail(url=ctx.guild.icon)

        return embed
    
    elif info_to_return == "ROLE":
        match next_role:
            case 0: return holiday1.id
            case 1: return holiday2.id
            case 2: return holiday3.id
            case 3: return holiday4.id
