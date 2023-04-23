import asyncio
from io import BytesIO
import time
import openai
import discord
import re
from tunables import tunables, GLOBAL_EMBED_COLOR
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
        self.clear_items()
        try: await self.msg.edit(view=self)
        except: pass
        self.stop()
    
    
    async def ainit(self) -> None:
        if self.mm.message.author.bot: return
        
        self.response['personality'] = await self.mm.channel.gpt_personality
        
        match self.ctype:
            case discord.ChannelType.text:
                if len(self.mm.message.content) > 0 and str(self.mm.channel.client.user.id) in self.mm.message.content.split()[0] and self.mm.message.author.id != self.mm.channel.client.user.id or \
                    (self.mm.message.reference is not None and self.mm.message.reference.resolved is not None and \
                        self.mm.message.reference.resolved.author.id == self.mm.channel.client.user.id):
                            if len(self.mm.message.content.split()) <= 1 and self.mm.message.content == f"<@{str(self.mm.channel.client.user.id)}>":
                                await self.mm.message.reply(
                                    content=f"Please use {tunables('SLASH_COMMAND_SUGGEST_HELP')} for help.",
                                    silent=True
                                )
                                await self.on_timeout()
                                return
                else:
                    await self.on_timeout()
                    return
                
                
            case discord.ChannelType.public_thread: pass
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
        
        self.msg = await self.mm.message.reply(
            content=tunables('LOADING_EMOJI'),
            silent=True,
            mention_author=False
        )
        return True
    
    
    async def __check_attachments(self, message: discord.Message) -> str|None:
        if len(message.attachments) == 0: return None
        if message.attachments[0].filename != "message.txt": return None
        return (await message.attachments[0].read()).decode()
    
    
    
    
    '''
    Add caching for file content
    '''
    async def __fetch_chats(self) -> bool:
        
        # If not in thread, do this
        refs = await self.__fetch_replies()
        
        # If in thread, do this
        # refs = await self.__fetch thread messages
        
        try:
            self.chat.append(
                {"role": "system", "content": self.response['personality']}
            )
            
    
            # Determine the string to append to chat or
            # cancel interaction if any replied messages
            # cannot be read.
            refs.reverse()                
            for m in refs:
                m: discord.Message
                mssg = None
                if m.content == "" and len(m.attachments) == 0:# or re.match(r"<@\d{15,30}>", m.content):
                    try:
                        mssg = m.embeds[0].description
                        if mssg == "" or mssg is None or mssg == []: raise Exception
                    except: return False
                else:
                    try: mssg = ' '.join(self.__remove_mention(m.content.split()))
                    except: pass
                
                
                # Decode message.txt, if applicable
                if len(m.attachments) > 0:
                    val = await self.__check_attachments(message=m)
                    if val is not None:
                        mssg = f"{mssg} (A file is attached, it has been decoded so you can read it:) {val}"
                    elif mssg == "" or mssg is None or mssg == []: return False # Could cause issues. Replace with continue if so
                
                
                # Add message to chat list
                if m.author.id == self.mm.channel.guild.me:
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
                    mssg = f"{mssg} (A file is attached, it has been decoded so you can read it:) {val}"
            self.chat.append(
                {"role": "user", "content": mssg}
            )

            return True
        except Exception as e:
            print(f"Error whilst fetching chats [ChatGPT]: {e}")
            return False
    
    
    
    async def __fetch_replies(self) -> list:
        try:
            refs = []
            if self.mm.message.reference is not None:
                
                refs = [self.mm.message.reference.resolved]
                
                i = 0
                while True:
                    if refs[-1].reference is not None and i <= tunables('MAX_CONSIDER_REPLIES_OPENAI'):
                        
                        cmsg = CachedMessage(message_id=refs[-1].reference.message_id)
                        await cmsg.ainit()
                        if refs[-1].reference.cached_message is not None:
                            m: discord.Message = refs[-1].reference.cached_message
                        elif cmsg.content is not None and cmsg.content != "":
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
                # Mention does not have to be first word
                msg.pop(i)
        return msg
    
    
    async def respond(self) -> None:
        self.clear_items()
        # if await self.mm.channel.gpt_mode == "NORMAL":
        #     self.add_item(RegenerateButton())
        
        print("*************")
        for i, c in enumerate(self.chat):
            print(f">> {i+1} {c}")
        print("*************")

        try:
            await asyncio.to_thread(self.__openai_interaction)
            
            resp_len = len(self.response['data'])
            if resp_len >= 750 and resp_len <= 3999:
                embed = await self.__embed()
                content = self.mm.user.user.mention
                await self.msg.delete()
                self.thread = await self.mm.message.create_thread(
                    name=f"{await self.mm.user.username} ChatGPT Session",
                    auto_archive_duration=60,
                    slowmode_delay=2,
                    reason="ChatGPT"
                )
                await self.thread.send(
                    content=self.response['data'],
                    silent=True,
                    allowed_mentions=discord.AllowedMentions(
                        replied_user=True,
                        users=True
                    )
                )
                return
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
            self.response['data'] = f"`{''.join(self.__remove_mention(self.mm.message.content))}`\n{text}"
            
        else: self.response['data'] = text