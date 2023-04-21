import asyncio
from io import BytesIO
import openai
import discord
import re
from tunables import tunables, GLOBAL_EMBED_COLOR
from Database.GuildObjects import MikoMember, GuildProfile, AsyncDatabase, MikoTextChannel, MikoMessage

db = AsyncDatabase('OpenAI.ai.py')

openai.api_key = tunables('OPENAI_API_KEY')

class MikoGPTT(discord.ui.View):
    def __init__(self, u: MikoMember, client: discord.Client, prompt: str):
        super().__init__(timeout=tunables('GLOBAL_VIEW_TIMEOUT'))
        self.u = u
        self.client = client
        self.prompt = prompt
        self.response = {
            'type': "NORMAL", # NORMAL, SERIOUS, IMAGE
            'data': None
        }
        self.__sanitize_prompt()
        self.context = None
    
    async def on_timeout(self) -> None:
        self.clear_items()
        try: await self.msg.edit(view=self)
        except: pass
    
    
    '''
    THINGS TO ADD:
    
    - consider which sender sent a message
    - change system context to discord chat bot
    - (done) message.txt for large messages
    
    '''
    
    
    async def respond(self, message: discord.Message=None, interaction: discord.Interaction=None, client: discord.Client=None) -> None:
        
        self.clear_items()
        # self.msg = message if message is not None else await interaction.original_response()
        ch = MikoTextChannel(
            channel=message.channel if message is not None else interaction.channel,
            client=client if message is not None else interaction.client
        )
        
        self.role = await ch.gpt_personality
        if self.role is None:
            await message.reply(content=tunables('OPENAI_NOT_ENABLED_IN_CHANNEL'))
            return
        
        self.msg = await message.reply(content=tunables('LOADING_EMOJI'), mention_author=False, silent=True) if message is not None else await interaction.original_response()
    
        if message is not None:
            # await self.msg.reply(content=tunables('LOADING_EMOJI'), mention_author=False, silent=True)
            
            try:
                if self.msg.reference is not None and self.context is not None:
                    refs = [self.msg.reference.resolved]
                    
                    i = 0
                    while True:
                        if refs[-1].reference is not None and i <= tunables('MAX_CONSIDER_REPLIES_OPENAI'):
                            
                            
                            if refs[-1].reference.cached_message is not None:
                                m: discord.Message = refs[-1].reference.cached_message
                            else:
                                m: discord.Message = await self.msg.channel.fetch_message(refs[-1].reference.message_id)
                                if m is None: continue


                            refs.append(m)
                            
                        else: break
                        
                        i+=1
                    
                    refs.reverse()
                    
                    
                    
                    self.context = []
                    self.context.append(
                        {"role": "system", "content": self.role}
                    )
                    for m in refs:
                        if m.content == "" or re.match(r"<@\d{15,30}>", m.content):
                            try:
                                mssg = m.embeds[0].description
                            except: continue
                        else:
                            mssg = ' '.join(self.__remove_mention(m.content.split()))
                        if m.author.id == m.guild.me.id:
                            self.context.append(
                                {"role": "assistant", "content": mssg}
                            )
                        else:
                            self.context.append(
                                {"role": "user", "content": mssg}
                            )
            except Exception as e:
                await self.msg.edit(
                    content=f"An error occurred when referencing previous messages: {e}"
                )
                return
                
        else:
            print("Error [OpenAI.ai.MikoGPT:respond()]: Could not respond because a 'Message' or 'Interaction' object was not passed.")
            return
    
        try:
            await asyncio.to_thread(self.__openai_interaction)

            if (len(self.response['data']) >= 750 or self.response['type'] == "IMAGE") and \
                len(self.response['data']) <= 3999:
                embed = await self.__embed()
                content = self.u.user.mention
            elif len(self.response['data']) >= 4000:
                embed = None
                content = self.u.user.mention
                b = bytes(self.response['data'], 'utf-8')
                await self.msg.edit(
                    content=(
                            "The response to your prompt was too long. I have sent it in this "
                            "`response.txt` file. You can view on PC or Web (or Mobile if you "
                            "are able to download the file)."
                        ),
                    attachments=[discord.File(BytesIO(b), "response.txt")]
                )
                return
            else:
                embed = None
                content = self.response['data']

            if await ch.gpt_mode == "NORMAL": self.add_item(RegenerateButton())
            await self.msg.edit(
                content=content,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(
                    replied_user=True
                ),
                view=self
            )
            await self.u.increment_statistic('REPLY_TO_MENTION_OPENAI')
        except Exception as e:
            print(f">> OpenAI Response Error: {e}")
            await self.u.increment_statistic('REPLY_TO_MENTION_OPENAI_REJECT')
            await self.msg.edit(
                content=f"{tunables('GENERIC_APP_COMMAND_ERROR_MESSAGE')[:-1]}: {e}"
            )
        
    def __remove_mention(self, msg: list) -> list:
        for i, word in enumerate(msg):
            if word in [f"<@{str(self.client.user.id)}>"]:
                # Remove word mentioning Miko
                # Mention does not have to be first word
                msg.pop(i)
        return msg
    
    def __sanitize_prompt(self) -> None:
        '''
        Clean up prompt and remove 'i:' and 's:'

        Determine whether response type is
        'IMAGE' or 'SERIOUS', if neither,
        keep type as 'NORMAL'
        '''
        
        self.prompt = self.__remove_mention(self.prompt.split())
        
        # if re.search('s:', self.prompt[0].lower()):
        #     if self.prompt[0].lower() == "s:":
        #         self.prompt.pop(0)
        #     else:
        #         self.prompt[0] = self.prompt[0][2:]
        #     self.response['type'] = "SERIOUS"
        # if re.search('i:', self.prompt[0].lower()):
        #     if self.prompt[0] == "i:":
        #         self.prompt.pop(0)
        #     else:
        #         self.prompt[0] = self.prompt[0][2:]
        #     self.response['type'] = "IMAGE"
    
    def __openai_interaction(self) -> None:
        prompt = ' '.join(self.prompt)

        if self.response['type'] != "IMAGE":
            
            if self.context is None:
                messages = [
                        {"role": "system", "content": self.role},
                        {"role": "user", "content": prompt}
                    ]
            else:
                self.context.append(
                    {"role": "user", "content": prompt}
                )
                messages = self.context
            
            
            resp = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=messages
                )
        else:
            resp = openai.Image.create(
                prompt=prompt,
                n=1,
                size="256x256"
            )

        
        if self.response['type'] != "IMAGE":
            r = r"^.+(\n){2}(.|\n)*$"
            text = resp.choices[0].message.content
            if re.match(r, text):
                self.response['data'] = f"`{' '.join(self.prompt)}`\n{text}"
                
            else: self.response['data'] = text
        else:
            url = resp.data[0].url
            self.response['data'] = url 
    
    async def __embed(self) -> discord.Embed:
        temp = []

        if self.response['type'] != "IMAGE":
            temp.append(
                # "```\n"
                f"{self.response['data']}"
                # "\n```"
            )
        else:
            temp.append(
                f"__Prompt__: `{' '.join(self.prompt)}`"
            )
        
        embed = discord.Embed(
            description=''.join(temp),
            color=GLOBAL_EMBED_COLOR
        )
        embed.set_author(
            icon_url=await self.u.user_avatar,
            name=f"Generated by {await self.u.username}"
        )
        embed.set_footer(
            text=f"{self.client.user.name} ChatGPT Integration [Beta]"
        )
        if self.response['type'] == "IMAGE":
            embed.set_image(
                url=self.response['data']
            )
        return embed


class RegenerateButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(
            style=discord.ButtonStyle.green,
            label="Regenerate",
            emoji=tunables('GENERIC_REFRESH_BUTTON'),
            custom_id="regen_button",
            row=1,
            disabled=False
        )
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await (await interaction.original_response()).delete()
        async with interaction.channel.typing():
            await self.view.respond()
        
        
        
class MikoGPT(discord.ui.View):
    def __init__(self, mm: MikoMessage):
        super().__init__(timeout=tunables('GLOBAL_VIEW_TIMEOUT'))
        self.mm = mm
        self.chat = []
        self.thread = None
        self.msg: discord.Message = None
        self.response = {
            'personality': None,
            'data': None
        }
    
    async def on_timeout(self) -> None:
        self.clear_items()
        try: await self.msg.edit(view=self)
        except: pass
    
    
    async def ainit(self) -> None:
        self.response['personality'] = await self.mm.channel.gpt_personality
        if not await self.__send_reply(): return
        if not await self.__fetch_replies(): return
        await self.respond()
        
    async def __send_reply(self) -> bool:
        if self.response['personality'] is None:
            if self.mm.message.reference is None:
                await self.mm.message.reply(
                    content=tunables('OPENAI_NOT_ENABLED_IN_CHANNEL'),
                    mention_author=True,
                    silent=True
                )
                return False
            else: return False
        
        self.msg = await self.mm.message.reply(
            content=tunables('LOADING_EMOJI'),
            silent=True,
            mention_author=False
        )
        return True
    
    
    '''
    Take a look at __fetch_replies again. Does not get the
    very first replied message
    '''
    async def __fetch_replies(self) -> bool:
        try:
            self.chat.append(
                {"role": "system", "content": self.response['personality']}
            )
            
            if self.mm.message.reference is not None:
                
                refs = [self.mm.message.reference.resolved]
                
                i = 0
                while True:
                    if refs[-1].reference is not None and i <= tunables('MAX_CONSIDER_REPLIES_OPENAI'):
                        
                        if refs[-1].reference.cached_message is not None:
                            m: discord.Message = refs[-1].reference.cached_message
                        else:
                            m: discord.Message = await self.mm.channel.channel.fetch_message(refs[-1].reference.message_id)
                            if m is None: continue
                        refs.append(m)
                    else: break
                    i+=1
                
                
                refs.reverse()
                for ref in refs:
                    print(ref.id, ref.content)


                for m in refs:
                        if m.content == "" or re.match(r"<@\d{15,30}>", m.content):
                            print("Inside first if")
                            try:
                                mssg = m.embeds[0].description
                            except: continue
                        else:
                            mssg = ' '.join(self.__remove_mention(m.content.split()))
                            
                        if m.author.id == m.guild.me.id:
                            self.chat.append(
                                {"role": "assistant", "content": mssg}
                            )
                        else:
                            
                            # If message is >4000 tokens, split responses
                            # into multiple list items. dont know if needed yet
                            self.chat.append(
                                {"role": "user", "content": f"{m.author.mention}: {mssg}"}
                            )
                        print(mssg)
            
            self.chat.append(
                {"role": "user", "content": f"{self.mm.user.user.mention}: {' '.join(self.__remove_mention(self.mm.message.content.split()))}"}
            )

            print("**************")
            for c in self.chat:
                print(f">> {c}")
            print("**************")

            return True
        except Exception as e:
            print(f"Error whilst fetching message replies [ChatGPT]: {e}")
            return False
              
    def __remove_mention(self, msg: list) -> list:
        for i, word in enumerate(msg):
            if word in [f"<@{str(self.mm.channel.client.user.id)}>"]:
                # Remove word mentioning Miko
                # Mention does not have to be first word
                msg.pop(i)
        return msg
    
    
    async def respond(self) -> None:
        self.clear_items()
        # if await self.mm.channel.gpt_mode == "NORMAL":
        #     self.add_item(RegenerateButton())
        
        # print(self.chat)

        try:
            await asyncio.to_thread(self.__openai_interaction)
            
            resp_len = len(self.response['data'])
            if resp_len >= 750 and resp_len <= 3999:
                self.thread = True
                embed = await self.__embed()
                content = self.mm.user.user.mention
            elif resp_len >= 4000:
                b = bytes(self.response['data'], 'utf-8')
                await self.msg.edit(
                    content=(
                            "The response to your prompt was too long. I have sent it in this "
                            "`response.txt` file. You can view on PC or Web (or Mobile if you "
                            "are able to download the file)."
                        ),
                    attachments=[discord.File(BytesIO(b), "response.txt")],
                )
                return
            else:
                embed = None
                content = self.response['data']
            
            
            await self.msg.edit(
                content=content,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(
                    replied_user=True,
                    users=True
                ),
                view=self
            )
            await self.mm.user.increment_statistic('REPLY_TO_MENTION_OPENAI')
        except Exception as e:
            await self.mm.user.increment_statistic('REPLY_TO_MENTION_OPENAI_REJECT')
            await self.msg.edit(
                content=f"{tunables('GENERIC_APP_COMMAND_ERROR_MESSAGE')[:-1]}: {e}",
                allowed_mentions=discord.AllowedMentions(
                    replied_user=False,
                    users=False
                )
            )
        
    async def __embed(self) -> discord.Embed:
        temp = []

        temp.append(f"{self.response['data']}")
        
        embed = discord.Embed(
            description=''.join(temp),
            color=GLOBAL_EMBED_COLOR
        )
        embed.set_author(
            icon_url=await self.mm.user.user_avatar,
            name=f"Generated by {await self.mm.user.username}"
        )
        embed.set_footer(
            text=f"{self.mm.channel.client.user.name} ChatGPT 3.5 Integration [Beta]"
        )
        return embed
    
    def __openai_interaction(self) -> None:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=self.chat
        )
        
        # If ChatGPT response contains original prompt,
        # put `` around that prompt.
        r = r"^.+(\n){2}(.|\n)*$"
        text = resp.choices[0].message.content
        if re.match(r, text):
            self.response['data'] = f"`{' '.join(self.__remove_mention(self.mm.message.content))}`\n{text}"
            
        else: self.response['data'] = text