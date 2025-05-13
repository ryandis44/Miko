'''
Main file for determining the model and API to use for
generative AI. This file is the main entry point for
all generative AI.

If any generative AI is enabled in a channel, **all
messages will be cached for 90 days in Redis**. This
is to ensure that the model has enough data to generate
a response and in a timely manner.
'''



import asyncio # for sleep
import discord
import logging
import re

from Database.MikoCore import MikoCore
from Database.Redis import RedisCache
from GenerativeAI.CachedObjects import CachedMessage
from GenerativeAI.OpenAI.ChatGPT import ChatGPT
from io import BytesIO # for message.md
from json import loads # for loading redis data
LOGGER = logging.getLogger()
r = RedisCache(__file__)



############################################################################################################



class CancelButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(
            label="Cancel",
            style=discord.ButtonStyle.red,
            emoji="✖",
            row=1,
            disabled=False
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.cancel(interaction)



class GenerativeAI(discord.ui.View):
    def __init__(self, mc: MikoCore) -> None:
        self.mc = mc
        self.t = discord.ChannelType
        self.text_response = None
        self.msg: discord.Message = None
        super().__init__(timeout=mc.tunables('GLOBAL_VIEW_TIMEOUT'))



    async def on_timeout(self) -> None: self.stop()
    
    
    # Entry point
    async def ainit(self) -> None:
        
        # Do not run any of this code if AI is disabled
        if self.mc.channel.channel_settings['ai_mode'] == "DISABLED": return
        
        try: self.ai_mode = self.mc.tunables(f'GENERATIVE_AI_MODE_{self.mc.channel.channel_settings['ai_mode']}')
        except:
            await self.mc.channel.set_ai_mode(mode="DISABLED")
            return
        
        '''
        If:
            - The message is from a bot that is not Miko
            - The message is from discord (system message)
            - The message is intentionally ignored (starts with '!')
            - The message is only a mention (no other content)
        Then return and do not:
            - Cache the message
            - Generate a response
            
        Else:
            - Cache the message and proceed
        '''
        
        
        
        ### TODO somewhere around here may have caused 'Task was destroyed but it is pending!' error for discord.py: on_message
        if self.mc.message.message.author.system or self.mc.message.message.content.startswith(self.mc.tunables('GENERATIVE_AI_MESSAGE_IGNORE_CHAR'))\
                or re.match(r"^((<@\d{15,22}>)\s*)+$", self.mc.message.message.content): return

        if self.mc.tunables('MESSAGE_CACHING'): await self.mc.message.cache_message()
        else: return # do not use Discord for AI caching; will result in rate limiting
        
        if self.mc.message.message.author.bot and self.mc.message.message.author.id == self.mc.channel.client.user.id: return # do not respond to yourself
        
        '''
        If not a thread and:
            - Message content is not empty
            - Message content contains a mention to Miko (first word)
            - Message is not from Miko or the message is referencing a message
              from Miko
        Then:
            Additionally if:
                - The message only contains a mention to Miko and does not have a prompt
            Then:
                - Return and do not generate a response
            Else:
                - Get context for the AI model (chat history); this is the message's content
        
        
        If a thread and:
            - Message content is not empty
            - Message is not from Miko
        Then:
            - Get context for the AI model (chat history); this is the thread's messages
        '''
        match self.mc.message.message.channel.type:
            
            case self.t.text | self.t.voice | self.t.news | self.t.forum | self.t.stage_voice:
                # If not a thread and ...
                if len(self.mc.message.message.content) > 0 and str(self.mc.channel.client.user.id) in self.mc.message.message.content.split()[0] \
                    and self.mc.message.message.author.id != self.mc.channel.client.user.id or (self.mc.message.message.reference is not None and \
                        self.mc.message.message.reference.resolved is not None and self.mc.message.message.reference.resolved.author.id == self.mc.channel.client.user.id):
                        # then ...
                        
                        # Additionally if ...
                        if (len(self.mc.message.message.content.split()) <= 1 and self.mc.message.message.content == f"<@{str(self.mc.channel.client.user.id)}>"):
                            await self.on_timeout()
                            return
                else:
                    await self.on_timeout()
                    return
            
            case self.t.public_thread | self.t.private_thread | self.t.news_thread:
                if not self.mc.tunables('FEATURE_ENABLED_AI_THREADS'):
                    await self.mc.message.message.reply('AI_THREADS_DISABLED_MESSAGE')
                    return
                
                try: await self.mc.message.message.channel.fetch_member(self.mc.user.client.user.id)
                except: return
                
                if (len(self.mc.message.message.content) == 0 and len(self.mc.message.message.attachments) == 0): return
            
            case _: # Unknown channel type, disable AI
                try: await self.mc.channel.set_ai_mode(mode="DISABLED")
                except: pass
                return

        await self.__fetch_chats()
        
        self.msg = await self.mc.message.message.reply(
            content=self.mc.tunables('LOADING_EMOJI'),
            silent=True,
            view=self,
            embed=None,
            mention_author=False
        )

        '''
        Branch out to the different AI models and APIs. At this point in the
        code, all generalized processing has been done and model-specific
        operations can be performed.
        '''
        try:
            i=0
            while True:
                match self.ai_mode['api']:
                    
                    case "openai": 
                        chatgpt = ChatGPT(mc=self.mc, ai_mode=self.ai_mode, chats=self.chats)
                        self.text_response = await chatgpt.ainit()
                    
                    case "mikoapi": LOGGER.critical("MikoAPI (Generative AI) is not yet implemented.")
                    
                    # Invalid API, revert to disabled
                    case _:
                        try: await self.mc.channel.set_ai_mode(mode="DISABLED")
                        except: raise Exception("Failed to set AI mode to 'DISABLED'")
                
                if i >= self.mc.tunables('GENERATIVE_AI_MAX_RETRIES'): raise Exception
                if self.text_response: break
                i+=1
                
                if i == 1: await self.msg.edit(
                    content=f"Still loading... {self.mc.tunables('LOADING_EMOJI')}",
                )
                await asyncio.sleep(2)
                
        except:
            LOGGER.error(f"Failed to generate '{self.ai_mode['api']}' response [Max retries reached]")
            await self.msg.edit(
                content=f"An error occurred while trying to generate a response. Please try again later.",
                embed=None,
                view=None
            )
            return
        
        # await self.msg.edit(
        #     content=self.text_response,
        #     embed=None,
        #     view=None
        # )
        
        
        '''
        Determine whether to create a thread, embed, or send a message
        Thread:
            - If the response is long enough for an embed, create thread
              (unless thread mode is set to 'DISABLED')
            - If threads are set to 'ALWAYS', create thread
        Embed:
            - If the response is 750 characters or more, create thread
        '''
        resp_len = len(self.text_response)
        if ((resp_len >= self.mc.tunables('GENERATIVE_AI_SEND_EMBED_THRESHOLD') and resp_len <= (self.mc.tunables('GLOBAL_MAX_MESSAGE_LENGTH') - 1)) or self.mc.channel.channel_settings['ai_threads'] == "ALWAYS"):
            embed = self.__embed()
            thread_content = (
                self.__thread_info() +
                "Please see my response below:"
            )
            if await self.__create_thread(
                    content=thread_content if resp_len >= self.mc.tunables('GENERATIVE_AI_SEND_EMBED_THRESHOLD') else thread_content + "\n\n" + self.text_response,
                    embed=embed if resp_len >= self.mc.tunables('GENERATIVE_AI_SEND_EMBED_THRESHOLD') else None,
                    attachments=None
                ): return
            
            await self.msg.edit(
                content=None if resp_len >= self.mc.tunables('GENERATIVE_AI_SEND_EMBED_THRESHOLD') else self.text_response,
                embed=embed if resp_len >= self.mc.tunables('GENERATIVE_AI_SEND_EMBED_THRESHOLD') else None,
                allowed_mentions=discord.AllowedMentions(
                    replied_user=True,
                    users=True,
                ),
                view=self
            )
            return

        elif resp_len >= self.mc.tunables('GLOBAL_MAX_MESSAGE_LENGTH'):
            b = bytes(self.text_response, 'utf-8')
            attachments = [discord.File(BytesIO(b), "message.md")]
            
            # Create thread with message.md and info
            if await self.__create_thread(
                content=(
                    self.__thread_info() + self.mc.tunables('GENERATIVE_AI_MESSAGE_TOO_LONG_MSG')
                ),
                embed=None,
                attachments=attachments
            ): return
            
            # Send message with message.md and info
            await self.msg.edit(
                content=(self.mc.tunables('GENERATIVE_AI_MESSAGE_TOO_LONG_MSG')),
                attachments=attachments,
                view=self
            )
            return
        
        # Set AllowedMentions to True now that a response has been generated
        await self.msg.edit(
            content=self.text_response,
            embed=None,
            allowed_mentions=discord.AllowedMentions(
                replied_user=True,
                users=True
            ),
            view=self
        )
        
        await self.mc.user.increment_statistic('GENERATIVE_AI_RESPONSES_GENERATED')



    async def __create_thread(self, content: str, embed: discord.Embed, attachments) -> bool:
        if self.mc.channel.channel_settings['ai_threads'] == "DISABLED" or (self.msg is not None and self.msg.channel.type in self.mc.threads): return False
        if self.mc.profile.feature_enabled('AI_THREADS') != 1: return False
        
        '''
        Miko will create a thread if:
            - It has private thread creation permission
            - AND it has manage threads permission
            - AND FINALLY the user interacting with Miko is able to
            send messages in threads.
            - OR if gpt_threads == "ALWAYS" and the above
            is satisfied
        '''
        create = self.mc.message.message.channel.permissions_for(self.mc.message.message.channel.guild.me).create_private_threads
        manage = self.mc.message.message.channel.permissions_for(self.mc.message.message.channel.guild.me).manage_threads
        user_can_send_messages = self.mc.message.message.channel.permissions_for(self.mc.user.user).send_messages_in_threads
        if self.mc.message.message.channel.type == discord.ChannelType.text and (create and manage and user_can_send_messages):
            if len(self.mc.message.message.content) > 0:
                name = ' '.join(self.mc.ai_remove_mention(self.mc.message.message.content.split()))
            else:
                name = self.mc.ai_remove_mention(self.mc.message.message.content.split())
                if len(name) > 0: name = ' '.join(name)
                else: name = ''.join(name)
            
            self.thread = await self.mc.message.message.channel.create_thread(
                name=name[0:90] if len(name) < 89 else name[0:90] + "...",
                auto_archive_duration=60,
                slowmode_delay=self.mc.tunables('GENERATIVE_AI_THREAD_SLOWMODE_DELAY'),
                reason="User-generated generative AI thread",
                invitable=True
            )
            temp = await self.thread.send(
                content=content,
                embed=embed,
                files=attachments,
                silent=True,
                allowed_mentions=discord.AllowedMentions(
                    replied_user=True,
                    users=True,
                )
                # view=self # Depreciated Miko 2.0 feature; TODO for 3.0
            )
            
            if self.msg is None:
                await self.mc.message.message.reply(
                    content=self.__thread_created_info(),
                    embed=None,
                    view=None
                )
            else: await self.msg.edit(
                content=self.__thread_created_info(),
                embed=None,
                view=None
            )
            
            # Assign thread to message that created it (so it can be referenced later in the thread)
            await self.mc.message.assign_cached_message_to_thread(thread=self.thread)
            
            return True



    def __embed(self) -> discord.Embed:
        temp = []
        temp.append(f"{self.text_response}")
        
        embed = discord.Embed(
            description=''.join(temp),
            color=self.mc.tunables('GLOBAL_EMBED_COLOR')
        )
        embed.set_author(
            icon_url=self.mc.user.miko_avatar,
            name=f"Generated by {self.mc.user.username}"
        )
        embed.set_footer(
            text=f"3.0-BETA 1  •  {self.ai_mode['value']}  •  {self.ai_mode['model']}  •  Max Context Length {self.ai_mode['input_tokens']:,} Tokens"
        )
        return embed



    def __thread_info(self) -> str:
        return (
            f"Hello {self.mc.message.message.author.mention}! I created a private thread that only you and "
            "I can see so I can better help answer your questions.\n\n"
            "Private threads are similar to a regular Group DM. If you would like to invite someone "
            "to this thread, just @ mention them and they will appear. They will be able to invite anyone else from "
            "this server once added. You and anyone else in this thread can leave it by right-clicking (or long pressing) "
            "on the thread in the channels side menu.\n\n"
            "Additionally, if you would like to message in this thread without me reading the message and responding to it, "
            "put an exclamation mark `!` at the beginning of your message and I will ignore it.\n\n"
            "Also, __**no need to @ mention me in this thread**__. I will respond to all messages that are not just an @ mention "
            "(for adding people to this thread)."
            "\n\n"
        )



    def __thread_created_info(self) -> str:
        return (
            f"I created a private thread that only you and I can access, {self.mc.message.message.author.mention}.\n"
            f"→ Jump to that thread: {self.thread.jump_url}"
        )



    async def __fetch_chats(self) -> bool:
        
        self.chats = await self.__fetch_replies()
        
        if len(self.chats) == 0:
            if self.mc.message.message.channel.type in self.mc.threads: # if in a thread
                self.chats = await self.__fetch_thread_messages()
        return True

    async def __fetch_replies(self) -> list:
        
        try:
            replies = []
            if self.mc.message.message.reference is not None:
                replies = [self.mc.message.message.reference.resolved]
                
                '''
                Logic here:
                We are looping to loop through an entire reply chain.
                - (Fastest) If the message has a reference (i.e. a reply), we
                  try fetching it from the internal Discord cache
                - (Idential speed as Discord) If not in the Discord cache,
                  we check the Redis cache
                - (Slowest) Else it is not in the Redis cache, we fetch the message
                  from Discord and cache it in Redis. Fetching is subject
                  to Discord's rate limits, which is why we use Redis
                '''
                i = 0
                while True:
                    if replies[-1].reference is not None and i <= self.mc.tunables('GENERATIVE_AI_MAX_REPLIES_CHAIN'):
                        cmsg = CachedMessage(message_id=replies[-1].reference.message_id)
                        await cmsg.ainit()
                        if replies[-1].reference.cached_message is not None:
                            m: discord.Message = replies[-1].reference.cached_message
                        elif cmsg.content != "" or len(cmsg.attachments) > 0 or len(cmsg.embeds) > 0:
                            m = cmsg
                        else:
                            m: discord.Message = await self.mc.message.message.channel.fetch_message(replies[-1].reference.message_id)
                            if m is None:
                                i+=1
                                continue
                            await cmsg.mc.message.ainit(message=m, client=self.mc.channel.client)
                            await cmsg.mc.message.cache_message()
                        replies.append(m)
                    else: break
                    i+=1
            return replies
        except Exception as e:
            LOGGER.error(f"Error fetching replies: {e}")
            return []



    async def __fetch_thread_messages(self) -> list:
        '''
        Simply retrieves the last GENERATIVE_AI_MAX_REDIS_QUERIED_THREAD_MESSAGES
        amount of thread messages (regardless of replies) and caches them inside
        Miko to be used for Generative AI
        '''
        messages = await r.search(
            query=self.mc.message.message.channel.id,
            type="JSON_THREAD_ID",
            index="by_thread_id",
            limit=self.mc.tunables('GENERATIVE_AI_MAX_REDIS_QUERIED_THREAD_MESSAGES')
        )
        
        replies = []
        for m in messages:
            m = CachedMessage(m=loads(m['json']))
            if (m.content != "" or len(m.attachments) > 0 or len(m.embeds) > 0) and m.id != self.mc.message.message.id:
                replies.append(m)
        return replies