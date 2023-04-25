import asyncio
from io import BytesIO
import time
import openai
import discord
import re
from tunables import *
from Database.GuildObjects import CachedMessage, MikoMember, GuildProfile, AsyncDatabase, RedisCache, MikoTextChannel, MikoMessage

db = AsyncDatabase('OpenAI.ai.py')
r = RedisCache('OpenAI.ai.py')

openai.api_key = tunables('OPENAI_API_KEY')


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
        self.response_extra_content = ""
        self.channel = mm.message.channel
        self.ctype = self.channel.type

        self.msg: discord.Message = None
        self.response = {
            'personality': None,
            'data': None
        }
        self.thread_types = [
            discord.ChannelType.public_thread,
            discord.ChannelType.private_thread,
            discord.ChannelType.news_thread
        ]
    
    async def on_timeout(self) -> None:
        # self.clear_items()
        # try: await self.msg.edit(view=self)
        # except: pass
        self.stop()
    
    
    async def ainit(self) -> None:
        if self.mm.message.author.bot: return
        self.gpt_threads = await self.mm.channel.gpt_threads
        
        self.response['personality'] = await self.mm.channel.gpt_personality
        
        self.t = discord.ChannelType
        match self.ctype:
            case self.t.text | self.t.voice | self.t.news | self.t.forum | self.t.stage_voice:
                if len(self.mm.message.content) > 0 and str(self.mm.channel.client.user.id) in self.mm.message.content.split()[0] and self.mm.message.author.id != self.mm.channel.client.user.id or \
                    (self.mm.message.reference is not None and self.mm.message.reference.resolved is not None and \
                        self.mm.message.reference.resolved.author.id == self.mm.channel.client.user.id):
                            if (len(self.mm.message.content.split()) <= 1 and self.mm.message.content == f"<@{str(self.mm.channel.client.user.id)}>") or \
                                (await self.mm.channel.profile).feature_enabled('CHATGPT') != 1:
                                await self.mm.message.reply(
                                    content=f"Please use {tunables('SLASH_COMMAND_SUGGEST_HELP')} for help.",
                                    silent=True
                                )
                                await self.on_timeout()
                                return
                    
                else:
                    await self.on_timeout()
                    return
                
                
            case self.t.public_thread | self.t.private_thread | self.t.news_thread:
                if not tunables('MESSAGE_CACHING'): return
                if (len(self.mm.message.content) == 0 and len(self.mm.message.attachments) == 0) or \
                    self.response['personality'] is None: return
                
                if re.match(r"^((<@\d{15,22}>)\s*)+$", self.mm.message.content): return
            case _: return
        
        if not await self.__fetch_chats(): return
        if not await self.__send_reply(): return
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
        
        
        
        if self.gpt_threads == "ALWAYS" and tunables('MESSAGE_CACHING'):
            if await self.__create_thread(
                content=(
                        self.__thread_info() +
                        "Generating response... " + tunables('LOADING_EMOJI')
                    ),
                embed=None,
                attachments=None
            ):
                self.response_extra_content = self.__thread_info()
                return True
        
        
        self.msg = await self.mm.message.reply(
            content=tunables('LOADING_EMOJI'),
            silent=True,
            mention_author=False
        )
        return True
    
    def __thread_created_info(self) -> str:
        return (
            f"I created a private thread that only you and I can access, {self.mm.message.author.mention}.\n"
            f"→ Jump to that thread: {self.thread.jump_url}"
        )
    
    def __thread_info(self) -> str:
        return (
            f"Hello {self.mm.message.author.mention}! I created a private thread that only you and "
            "I can see so I can better help answer your questions.\n\n"
            "Private threads are similar to a regular Group DM. If you would like to invite someone "
            "to this thread, just @ mention them and they will appear. They will be able to invite anyone else from "
            "this server once added. You and anyone else in this thread can leave it by right-clicking (or long pressing) "
            "on the thread in the channels side menu."
            "\n\n"
        )
    
    async def __check_attachments(self, message: discord.Message|CachedMessage) -> str|None:
        if len(message.attachments) == 0: return None
        if message.attachments[0].filename != "message.txt": return None
        try: return (await message.attachments[0].read()).decode()
        except:
            try: return message.attachments[0].data
            except: return None
    

    async def __fetch_chats(self) -> bool:
        
        # If not in thread, do this
        refs = await self.__fetch_replies()
        
        if len(refs) == 0:
            if self.ctype in THREAD_TYPES:
                refs = await self.__fetch_thread_messages()
        
        try:
            self.chat.append(
                {"role": "system", "content": self.response['personality']}
            )
            
    
            # Determine the string to append to chat or
            # cancel interaction if any replied messages
            # cannot be read.
            refs.reverse()
            for m in refs:
                # if type(m) == discord.Message:
                #     print(f">>> DISCORD: {m.content}")
                # else:
                #     print(f">>> REDIS: {m.content} {None if len(m.attachments) == 0 else m.attachments[0].data}")
                m: discord.Message|CachedMessage
                mssg = None
                if m.content == "" and len(m.attachments) == 0:# or re.match(r"<@\d{15,30}>", m.content):
                    try:
                        mssg = m.embeds[0].description
                        if mssg == "" or mssg is None or mssg == []: raise Exception
                    except: return False
                else:
                    try:
                        if re.match(r"^((<@\d{15,22}>)\s*)+$", m.content): continue # Ignore @ mentions in threads (all users)
                        if "Jump to that thread:" in m.content: return False # Ignore jump to thread message in parent channel
                        mssg = ' '.join(self.__remove_mention(m.content.split()))
                        if mssg == tunables('LOADING_EMOJI'): continue # ignore unresponded messages
                        for embed in m.embeds:
                            if embed.description == "" or embed.description is None: continue
                            mssg += " " + embed.description
                    except: pass
                
                
                # Decode message.txt, if applicable
                if len(m.attachments) > 0:
                    val = await self.__check_attachments(message=m)
                    if val is not None:
                        mssg = f"{mssg} {val}"
                    elif mssg == "" or mssg is None or mssg == []: return False # Could cause issues. Replace with continue if so
                
                
                # Add message to chat list
                if m.author.id == self.mm.channel.guild.me.id:
                    self.chat.append(
                        {"role": "assistant", "content": mssg}
                    )
                else:
                    # If message is >4000 tokens, split responses
                    # into multiple list items. dont know if needed yet
                    self.chat.append(
                        {"role": "user", "content": f"{m.author.mention}: {mssg}"}
                    )
        
            # Add latest message to end of chat list
            mssg = f"{self.mm.user.user.mention}: {' '.join(self.__remove_mention(self.mm.message.content.split()))}"
            if len(self.mm.message.attachments) > 0:
                val = await self.__check_attachments(message=self.mm.message)
                if val is not None:
                    mssg = f"{mssg} {val}"
            self.chat.append(
                {"role": "user", "content": mssg}
            )

            return True
        except Exception as e:
            print(f"Error whilst fetching chats [ChatGPT]: {e}")
            return False
    
    
    async def __fetch_thread_messages(self) -> list:
        if not tunables('MESSAGE_CACHING'): return
        messages = await r.search(
            query=self.channel.id,
            type="JSON_THREAD_ID",
            index="by_thread_id",
            limit=tunables('CHATGPT_THREAD_MESSAGE_LIMIT')
        )
        
        refs = []
        for m in messages:
            m = CachedMessage(m=loads(m['json']))
            if (m.content != "" or len(m.attachments) > 0 or len(m.embeds) > 0) and m.id != self.mm.message.id:
                refs.append(m)
        return refs
    
    
    async def __fetch_replies(self) -> list:
        try:
            refs = []
            if self.mm.message.reference is not None:
                
                refs = [self.mm.message.reference.resolved]
                
                i = 0
                while True:
                    if refs[-1].reference is not None and i <= tunables('CHATGPT_MAX_REPLIES_CHAIN'):
                        
                        cmsg = CachedMessage(message_id=refs[-1].reference.message_id)
                        await cmsg.ainit()
                        if refs[-1].reference.cached_message is not None:
                            m: discord.Message = refs[-1].reference.cached_message
                        elif cmsg.content != "" or len(cmsg.attachments) > 0 or len(cmsg.embeds) > 0:
                            m = cmsg
                        else:
                            m: discord.Message = await self.channel.fetch_message(refs[-1].reference.message_id)
                            if m is None:
                                i+=1
                                continue
                            mm = MikoMessage(message=m, client=self.mm.channel.client)
                            await mm.ainit(check_exists=False)
                        refs.append(m)
                    else: break
                    i+=1
                
            return refs
        except Exception as e:
            print(f"Error whilst fetching message replies [ChatGPT]: {e}")
            return []
              
    def __remove_mention(self, msg: list) -> list:
        for i, word in enumerate(msg):
            if word in [f"<@{str(self.mm.channel.client.user.id)}>"]:
                # Remove word mentioning Miko
                msg.pop(i)
        return msg
    
    
    async def respond(self) -> None:
        self.clear_items()
        # if await self.mm.channel.gpt_mode == "NORMAL":
        #     self.add_item(RegenerateButton())
        
        # print("*************")
        # print(f"GPT Threads Mode: {self.gpt_threads}")
        # for i, c in enumerate(self.chat):
        #     print(f">> {i+1} {c}")
        # print("*************")

        try:
            await asyncio.to_thread(self.__openai_interaction)
            
            resp_len = len(self.response['data'])
            if resp_len >= 750 and resp_len <= 3999:
                embed = await self.__embed()
                
                
                thread_content = (self.__thread_info() +
                    "Please see my response below:"
                )
                if await self.__create_thread(content=thread_content, embed=await self.__embed(), attachments=None): return
                
                await self.msg.edit(
                        content=None if self.response_extra_content == "" else self.response_extra_content + "Please see my response below:",
                        embed=embed,
                        allowed_mentions=discord.AllowedMentions(
                            replied_user=True,
                            users=True
                        )
                    )
                return
                
            elif resp_len >= 4000:
                b = bytes(self.response['data'], 'utf-8')
                attachments = [discord.File(BytesIO(b), "message.txt")]
                
                if await self.__create_thread(
                        content=(self.__thread_info() +
                            "The response to your prompt was too long. I have sent it in this "
                            "`message.txt` file. You can view on PC or Web (or Mobile if you "
                            "are able to download the file)."
                        ),
                        embed=None,
                        attachments=attachments
                    ): return
                
                await self.msg.edit(
                    content=(self.response_extra_content +
                            "The response to your prompt was too long. I have sent it in this "
                            "`message.txt` file. You can view on PC or Web (or Mobile if you "
                            "are able to download the file)."
                        ),
                    attachments=attachments,
                )
                return
            else:
                embed = None
                content = self.response['data']

            await self.msg.edit(
                content=content if self.response_extra_content == "" else self.response_extra_content + content,
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
            
    async def __create_thread(self, content: str, embed: discord.Embed, attachments) -> bool:

        if self.gpt_threads is None or (self.msg is not None and self.msg.channel.type in THREAD_TYPES): return False
        if (await self.mm.channel.profile).feature_enabled('CHATGPT_THREADS') != 1: return False

        '''
        Miko will create a thread if:
            - It has private thread creation permission
            - AND it has manage threads permission
            - AND FINALLY the user interacting with Miko is able to
            send messages in threads.
            - OR if gpt_threads == "ALWAYS" and has permission
        '''
        create = self.channel.permissions_for(self.channel.guild.me).create_private_threads
        manage = self.channel.permissions_for(self.channel.guild.me).manage_threads
        user = self.channel.permissions_for(self.mm.message.author).send_messages_in_threads
        # if self.ctype not in self.thread_types and (create and manage):# and len(self.chat) <= 2:
        if self.ctype == discord.ChannelType.text and (create and manage and user):# and len(self.chat) <= 2:
            if len(self.mm.message.content) > 90:
                name = ' '.join(self.__remove_mention(self.mm.message.content.split()))
            else:
                name = self.__remove_mention(self.mm.message.content.split())
                if len(name) > 1: name = ' '.join(name)
                else: name = ''.join(name)
            
            # self.thread = await self.mm.message.create_thread(
            #     name=name,
            #     auto_archive_duration=60,
            #     slowmode_delay=tunables('CHATGPT_THREAD_SLOWMODE_DELAY'),
            #     reason=f"User requested ChatGPT response"
            # )
            self.thread = await self.channel.create_thread(
                name=name[0:90] if len(name) < 89 else name[0:90] + "...",
                auto_archive_duration=60,
                slowmode_delay=tunables('CHATGPT_THREAD_SLOWMODE_DELAY'),
                reason=f"User requested ChatGPT response",
                invitable=True
            )
            temp = await self.thread.send(
                content=content,
                embed=embed,
                files=attachments,
                silent=True,
                allowed_mentions=discord.AllowedMentions(
                    replied_user=True,
                    users=True
                )
            )
            
            if self.msg is None:
                await self.mm.message.reply(
                    content=self.__thread_created_info(),
                    embed=None,
                    view=None
                )
                self.msg = temp
                return True
            
            await self.msg.edit(
                embed=None,
                view=None,
                content=self.__thread_created_info()
            )
            return True
        return False
        
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
            text=f"{self.mm.channel.client.user.name} ChatGPT 3.5 Integration v1.0"
        )
        return embed
    
    def __openai_interaction(self) -> None:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=self.chat
        )
        
        # If ChatGPT response contains original prompt,
        # put `` around that prompt.
        # r = r"^.+(\n){2}(.|\n)*$"
        text = resp.choices[0].message.content
        self.response['data'] = text
        # if re.match(r, text):
        #     self.response['data'] = f"`{''.join(self.__remove_mention(self.mm.message.content))}`\n{text}"
            
        # else: self.response['data'] = text