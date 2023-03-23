import asyncio
import openai
import discord
import re
from tunables import tunables, GLOBAL_EMBED_COLOR
from Database.GuildObjects import MikoMember

openai.api_key = tunables('OPENAI_API_KEY')

class MikoGPT:
    def __init__(self, u: MikoMember, client: discord.Client, prompt: str):
        self.u = u
        self.client = client
        self.prompt = prompt
        self.response = {
            'type': "NORMAL", # NORMAL, SERIOUS, IMAGE
            'data': None
        }
        self.__sanitize_prompt()
        self.context = None
    
    async def respond(self, message: discord.Message=None, interaction: discord.Interaction=None) -> None:
    
        if message is not None:
            msg = await message.reply(content=tunables('LOADING_EMOJI'), mention_author=False, silent=True)
            
            try:
                if message.reference is not None:
                    refs = [message.reference.resolved]
                    
                    i = 0
                    while True:
                        if refs[-1].reference is not None and i <= tunables('MAX_CONSIDER_REPLIES_OPENAI'):
                            
                            
                            if refs[-1].reference.cached_message is not None:
                                m: discord.Message = refs[-1].reference.cached_message
                            else:
                                m: discord.Message = await message.channel.fetch_message(refs[-1].reference.message_id)
                                if m is None: continue


                            refs.append(m)
                            
                        else: break
                        
                        i+=1
                    
                    refs.reverse()
                    
                    self.context = []
                    self.context.append(
                        {"role": "system", "content": tunables('OPENAI_RESPONSE_ROLE_DEFAULT')}
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
                await message.edit(
                    content=f"An error occurred when referencing previous messages: {e}"
                )
                return
                
        elif interaction is not None:
            msg = await interaction.original_response()
        else:
            print("Error [OpenAI.ai.MikoGPT:respond()]: Could not respond because a 'Message' or 'Interaction' object was not passed.")
            return
    
        try:
            block = asyncio.to_thread(self.__openai_interaction)
            await block

            if len(self.response['data']) >= 750 or self.response['type'] == "IMAGE":
                embed = self.__embed()
                content = self.u.user.mention
            else:
                embed = None
                content = self.response['data']

            await msg.edit(
                content=content,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(
                    replied_user=True
                )
            )
            self.u.increment_statistic('REPLY_TO_MENTION_OPENAI')
        except Exception as e:
            print(f">> OpenAI Response Error: {e}")
            self.u.increment_statistic('REPLY_TO_MENTION_OPENAI_REJECT')
            await msg.edit(
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
        
        if re.search('s:', self.prompt[0].lower()):
            if self.prompt[0].lower() == "s:":
                self.prompt.pop(0)
            else:
                self.prompt[0] = self.prompt[0][2:]
            self.response['type'] = "SERIOUS"
        if re.search('i:', self.prompt[0].lower()):
            if self.prompt[0] == "i:":
                self.prompt.pop(0)
            else:
                self.prompt[0] = self.prompt[0][2:]
            self.response['type'] = "IMAGE"
    
    def __openai_interaction(self) -> None:
        prompt = ' '.join(self.prompt)

        if self.response['type'] != "IMAGE":
            
            role = tunables('OPENAI_RESPONSE_ROLE_DEFAULT')
            match self.response['type']:
                case 'SERIOUS' | 'IMAGE':
                    role = tunables('OPENAI_RESPONSE_ROLE_DEFAULT')
                
                case _:
                    if self.u.profile.feature_enabled('REPLY_TO_MENTION_OPENAI_SARCASTIC'):
                        role = tunables('OPENAI_RESPONSE_ROLE_SARCASTIC')
            
            if self.context is None:
                messages = [
                        {"role": "system", "content": role},
                        {"role": "user", "content": prompt}
                    ]
            else:
                self.context.append(
                    {"role": "user", "content": prompt}
                )
                messages = self.context
            
            # for m in messages:
            #     print(m)
            
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
    
    def __embed(self) -> discord.Embed:
        temp = []

        if self.response['type'] != "IMAGE":
            temp.append(
                "```\n"
                f"{self.response['data']}\n"
                "```"
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
            icon_url=self.u.user_avatar,
            name=f"Generated by {self.u.username}"
        )
        embed.set_footer(
            text=f"{self.client.user.name} OpenAI/ChatGPT Integration [Beta]"
        )
        if self.response['type'] == "IMAGE":
            embed.set_image(
                url=self.response['data']
            )
        return embed