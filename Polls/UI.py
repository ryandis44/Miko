import asyncio
import time
import discord
from discord.ui import View
from misc.misc import emojis_1to10
from tunables import *
from utils.HashTable import HashTable
from Database.GuildObjects import MikoMember

active_polls = HashTable(10_000)

class PollCreateModal(discord.ui.Modal, title="New Poll"):

    name = discord.ui.TextInput(
            label="Poll Question:",
            placeholder="Do you like hot or cold weather?",
            max_length=tunables('POLL_MAX_TITLE_LENGTH')
        )
    answer = discord.ui.TextInput(
            label="Poll Answers (separated by line):",
            style=discord.TextStyle.paragraph,
            placeholder="Yes\nNo\nI love cold weather\nI love hot weather",
            max_length=tunables('POLL_MAX_BODY_LENGTH')
        )
    async def on_submit(self, interaction: discord.Interaction) -> None:

        view = PollDurationView(interaction=interaction, modal=self)
        await interaction.response.send_message(content=f"When do you want this poll to expire? (This message will expire <t:{int(time.time()) + tunables('EPHEMERAL_VIEW_TIMEOUT')}:R>)", view=view, ephemeral=True)

class PollDurationView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, modal):
        self.modal_interaction = interaction
        super().__init__(timeout=tunables('EPHEMERAL_VIEW_TIMEOUT'))
        self.add_item(PollDuration(modal=modal))

    async def on_timeout(self) -> None:
        # await self.modal_interaction.edit_original_response(view=None, content=tunables('GENERIC_MESSAGE_TIMEOUT_MESSAGE'))
        await self.modal_interaction.delete_original_response()
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        await self.modal_interaction.edit_original_response(content=f"Creating poll...", view=None)
        return True

class PollDuration(discord.ui.Select):
    '''
    The purpose of this view is to allow the user to
    set the duration of their poll. Discord Modals do
    not allow dropdown menus so we have to create a
    separate view to achieve this.
    '''
    
    def __init__(self, modal: PollCreateModal):
        self.modal = modal

        options = []
        # options.append(
        #     discord.SelectOption(
        #         label="[DEV]5 seconds",
        #         description=None,
        #         value=5,
        #         emoji=None
        #     )
        # )
        options.append(
            discord.SelectOption(
                label="5 minutes",
                description=None,
                value=300,
                emoji=None
            )
        )
        options.append(
            discord.SelectOption(
                label="15 minutes",
                description=None,
                value=900,
                emoji=None
            )
        )
        options.append(
            discord.SelectOption(
                label="30 minutes",
                description=None,
                value=1800,
                emoji=None
            )
        )
        options.append(
            discord.SelectOption(
                label="1 hour",
                description=None,
                value=3600,
                emoji=None
            )
        )
        options.append(
            discord.SelectOption(
                label="6 hours",
                description=None,
                value=21600,
                emoji=None
            )
        )
        options.append(
            discord.SelectOption(
                label="12 hours",
                description=None,
                value=43200,
                emoji=None
            )
        )
        options.append(
            discord.SelectOption(
                label="24 hours",
                description=None,
                value=86400,
                emoji=None
            )
        )

        super().__init__(placeholder="Poll Duration", max_values=1, min_values=1, options=options)
    async def callback(self, interaction: discord.Interaction):
        expiration = int(time.time()) + int(self.values[0])
        u = MikoMember(user=interaction.user, client=interaction.client)

        temp = []
        temp.append("\n")
        temp.append(f"\nExpires: __<t:{expiration}:R>__")
        temp.append("\n\n")
        ans = str(self.modal.answer).split("\n")

        i = 0 # cannot use enumerate() here
        while True:
            if ans[i] == "" or ans[i] == [] or ans[i] is None or ans[i] == "\n" or ans[i] == str():
                del ans[i]
                continue
            temp.append(f"{emojis_1to10(i)} {ans[i]}")
            temp.append("\n")
            i += 1
            if i >= len(ans): break

        embed = discord.Embed (
            title=self.modal.name,
            color = GLOBAL_EMBED_COLOR,
            description=f"{''.join(temp)}"
        )
        embed.set_author(
                name=f"{await u.username} Created a Poll",
                icon_url=await u.user_avatar
            )
        embed.set_footer(text="0 Responses Recorded. Polls are anonymous.")

        msg = await interaction.channel.send(content=f"{u.user.mention} created a poll")
        view = PollView(interaction=interaction, ans=ans, name=self.modal.name, author=u, expiration=expiration, embed=embed, temp=temp, original_message=msg)
        await u.increment_statistic('POLLS_CREATED')
        active_polls.set_val(key=f"{msg.id}", val=view)
        await msg.edit(embed=embed, view=view, content=None)
        await view.timer()
        


'''
Controlling class. This class has access to all poll information and
is responsible for expiring polls that have ended.
'''
class PollView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, ans: list, name, author: MikoMember, expiration: int, embed: discord.Embed, temp: list, original_message: discord.Message):
        self.original_interaction = interaction
        self.original_message = original_message
        self.author = author
        self.embed = embed
        self.temp = temp
        self.name = name
        self.ans = ans
        self.expiration = expiration
        self.count = 0
        self.author_guild_avatar = author.user.guild_avatar
        self.responses = HashTable(10_000)
        self.running = True
        super().__init__(timeout=86401)
        self.add_item(Poll(ans=ans, responses=self.responses, poll=self))
        self.add_item(PollEnd(author=author, poll=self))
        self.add_item(PollYourResponse(responses=self.responses, ans=self.ans))
        self.add_item(PollOngoingResults(author=author, responses=self.responses, ans=self.ans, name=self.name))
        
    
    async def refresh_count(self) -> None:
        responses = len(self.responses.get_all)
        if self.count != responses:
            self.count = responses
            self.embed.set_footer(text=f"{self.count:,} {'Responses' if self.count > 1 or self.count == 0 else 'Response'} Recorded. Polls are anonymous.")
            await self.original_message.edit(embed=self.embed)

    async def timer(self):
        s = int(time.time())
        while self.running:
            if s >= self.expiration:
                await self.end()
                return

            if s % 10 == 0: await self.refresh_count()
            await asyncio.sleep(1)
            s += 1

    def terminate(self) -> None:
        self.stop()
        self.running = False

    async def end(self, mention=True) -> None:
        self.terminate()
        responses = self.responses.get_all
        res_msg: discord.Message = await self.original_interaction.channel.send(
            embed=results_embed(responses=responses, author=self.author, ans=self.ans, name=self.name),
            content=self.author.user.mention if mention else None
        )
        
        url = (
            "https://discord.com/channels/"
            f"{self.original_interaction.guild_id}/"
            f"{self.original_interaction.channel_id}/"
            f"{res_msg.id}"
        )
        await self.original_message.edit(
            content=None,
            embed=discord.Embed(
                title="This poll has ended.",
                description=(
                    f"[Click Me]({url}) to view results."
                    "\n\nCreate a new one with:\n"
                    "</poll create:1060803394408829038>"
                ),
                color=GLOBAL_EMBED_COLOR
            ),
            view=None
        )
        active_polls.delete_val(key=f"{self.original_message.id}")

    async def on_timeout(self) -> None:
        await self.end()

class PollEnd(discord.ui.Button):
    def __init__(self, author: MikoMember, poll: PollView):
        self.author = author
        self.poll = poll
        super().__init__(style=discord.ButtonStyle.red, emoji=None, label="End", custom_id="poll:end", disabled=False, row=2)
    async def callback(self, interaction: discord.Interaction):
        
        ch_perms = interaction.channel.permissions_for(interaction.user).manage_messages
        # ch_perms = False
        if interaction.user.id != self.author.user.id and interaction.user and not ch_perms:
            await interaction.response.send_message(content=tunables('POLL_END_NOT_AUTHOR'), ephemeral=True)
            msg = await interaction.original_response()
            await asyncio.sleep(5)
            await msg.delete()
            return

        if interaction.user.id == self.author.user.id: 
            resp = 'their'
            await self.author.increment_statistic('POLLS_ENDED')
        else:
            resp = f'{self.author.user.mention}\'s'
            u = MikoMember(user=interaction.user, client=interaction.client)
            await u.increment_statistic('POLLS_ENDED')
        await interaction.response.send_message(content=f"{interaction.user.mention} ended {resp} poll early")
        await self.poll.end(mention=False)

class PollOngoingResults(discord.ui.Button):
    def __init__(self, author: MikoMember, responses: HashTable, ans: list, name: str):
        self.author = author
        self.responses = responses
        self.ans = ans
        self.name = name
        super().__init__(style=discord.ButtonStyle.gray, emoji=None, label="View Current Results", custom_id="poll:ongoing_results", disabled=False, row=2)
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=await ongoing_results(author=self.author, responses=self.responses, ans=self.ans, name=self.name), ephemeral=True)
        msg = await interaction.original_response()
        await asyncio.sleep(30)
        await msg.delete()


class PollYourResponse(discord.ui.Button):
    def __init__(self, responses: HashTable, ans: list):
        self.responses = responses
        self.ans = ans
        super().__init__(style=discord.ButtonStyle.blurple, emoji=None, label="Your Response", custom_id="poll:your_response", disabled=False, row=2)
    async def callback(self, interaction: discord.Interaction):
        
        resp = self.responses.get_val(interaction.user.id)
        if resp is None:
            await interaction.response.send_message(
                content=tunables('POLL_NOT_YET_RESPONDED_MESSAGE'),
                ephemeral=True
            )
        
        else:
            choice = self.ans[int(resp)]
            await interaction.response.send_message(
                content=(
                    "You chose:\n"
                    f"{emojis_1to10(int(resp))} {choice}\n"
                ),
                ephemeral=True
            )
        msg = await interaction.original_response()
        await asyncio.sleep(5)
        await msg.delete()

class Poll(discord.ui.Select):
    '''
    The purpose of this view is to allow the user to
    set the duration of their poll. Discord Modals do
    not allow dropdown menus so we have to create a
    separate view to achieve this.
    '''
    
    def __init__(self, ans: list, responses: HashTable, poll: PollView):
        self.ans = ans
        self.poll = poll
        self.responses = responses

        options = []
        for i, a in enumerate(ans):
            options.append(
                discord.SelectOption(
                    label=a,
                    description=None,
                    value=i,
                    emoji=emojis_1to10(i)
                )
            )
            if i >= 10: break
        
        options.append(
            discord.SelectOption(
                label="Remove Response",
                description=None,
                value=-1,
                emoji="❌"
            )
        )

        super().__init__(placeholder="Poll Answers", max_values=1, min_values=1, options=options, row=1)
    async def callback(self, interaction: discord.Interaction):
        
        if self.values == [] or int(self.values[0]) == -1:

            resp = self.responses.get_val(key=interaction.user.id)
            await interaction.response.send_message(
                content=(
                    f"{tunables('POLL_NOT_YET_RESPONDED_MESSAGE') if resp is None else 'Response removed'}\n"
                ),
                ephemeral=True
            )
            if resp is not None: self.responses.delete_val(key=interaction.user.id)
        else:
            choice = int(self.values[0])
            self.responses.set_val(key=interaction.user.id, val=choice)

            await interaction.response.send_message(
                content=(
                    f"Response recorded. You chose:\n"
                    f"{emojis_1to10(choice)} {self.ans[choice]}\n"
                ),
                ephemeral=True,
            )
        msg = await interaction.original_response()
        await asyncio.sleep(5)
        await msg.delete()


async def results_embed(responses: list, author: discord.Member, ans: list, name) -> discord.Embed:

        temp = []
        temp.append("\n")

        answers_dict = {}
        for answer in ans:
            answers_dict[answer] = 0

        for response in responses:
            answers_dict[ans[int(response[0][1])]] += 1

        sorted_answers = sorted(answers_dict.items(), key=lambda x:x[1], reverse=True)

        temp.append("\n")
        temp.append(f":crown: __`{sorted_answers[0][0]}`__ won with **{sorted_answers[0][1]}** {'votes' if sorted_answers[0][1] > 1 or sorted_answers[0][1] == 0 else 'vote'}")

        if len(sorted_answers) > 1:
            temp.append("\n\n")
            temp.append(f"**All results**:\n")
            for i, resp in enumerate(sorted_answers):
                if i == 0: continue
                temp.append(f"\u200b \u200b {emojis_1to10(i)}  `{resp[0]}` had `{resp[1]}` {'votes' if resp[1] > 1 or resp[1] == 0 else 'vote'}")
                temp.append("\n")

        embed = discord.Embed (
            title=name,
            color = GLOBAL_EMBED_COLOR,
            description=f"{''.join(temp)}"
        )
        embed.set_author(
                name=f"{await author.username}'s Poll Results",
                icon_url=await author.user_avatar
            )
        
        return embed


async def ongoing_results(author: MikoMember, responses: HashTable, ans: list, name: str) -> discord.Embed:


        # poll: PollView = active_polls.get_val(key=f"{author.id}{interaction.guild.id}")
        # author = poll.author
        responses = responses.get_all

        temp = []
        temp.append("\n")

        answers_dict = {}
        for answer in ans:
            answers_dict[answer] = 0

        for response in responses:
            answers_dict[ans[int(response[0][1])]] += 1

        sorted_answers = sorted(answers_dict.items(), key=lambda x:x[1], reverse=True)

        temp.append("\n\n")
        temp.append(f"**All results**:\n")
        for i, resp in enumerate(sorted_answers):
            temp.append(f"\u200b \u200b {emojis_1to10(i)}  `{resp[0]}` has `{resp[1]}` {'votes' if resp[1] > 1 or resp[1] == 0 else 'vote'}")
            temp.append("\n")

        embed = discord.Embed (
            title=name,
            color = GLOBAL_EMBED_COLOR,
            description=f"{''.join(temp)}"
        )
        embed.set_author(
                name=f"{await author.username}'s Ongoing Poll Results",
                icon_url=await author.user_avatar
            )
        
        return embed