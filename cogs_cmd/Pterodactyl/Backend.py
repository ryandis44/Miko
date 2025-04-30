'''

Backend API calls for Pterodactyl

'''



import aiohttp
import asyncio
import discord
import time

from Database.MikoCore import MikoCore
from Database.MySQL import AsyncDatabase
from misc.misc import replace_line_in_string
db = AsyncDatabase(__file__)



class PterodactylActions:
    
    def __init__(self, mc: MikoCore, interaction: discord.Interaction):
        
        self.mc = mc
        self.interaction = interaction
        
        self.__string = ""
        self.last_update = 0
        self.servers = {}
    
    
    
    async def __msg(self, signal: str) -> None:
        
        self.msg = await self.interaction.original_response()
        if self.servers == {}: await self.__get_all_servers_details()
        else: await self.__get_server_details()
        
        server_list = f"\n".join([f"{self.mc.tunables('LOADING_EMOJI')} · {details['name']}" for server_id, details in self.servers.items()])
        
        self.__string = f"Running `{signal}` command on:\n{server_list}"
        
        self.msg = await self.msg.edit(content=self.__string)
        
        
        
    async def __get_server_details(self) -> dict:
        
        async with aiohttp.ClientSession() as session:
            
            for server_id, details in self.servers.items():
                
                url = f"{self.mc.tunables('PTERODACTYL_PANEL_URL')}/api/client/servers/{server_id}"
                
                headers = {
                    'Authorization': f'Bearer {self.mc.tunables("PTERODACTYL_API_KEY")}',
                    'Content-Type': 'application/json',
                }
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.servers[server_id] = {
                            'name': data['attributes']['name'],
                        }
        
        
        
    async def __get_all_servers_details(self) -> dict:
        
        self.servers = {}
        
        async with aiohttp.ClientSession() as session:
            
            for server_id in self.mc.tunables('KGB_SERVER_IDS').splitlines():
                
                url = f"{self.mc.tunables('PTERODACTYL_PANEL_URL')}/api/client/servers/{server_id}"
                
                headers = {
                    'Authorization': f'Bearer {self.mc.tunables("PTERODACTYL_API_KEY")}',
                    'Content-Type': 'application/json',
                }
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.servers[server_id] = {
                            'name': data['attributes']['name'],
                        }

    
    
    async def __update_message(self, force=False) -> None:
        
        now = int(time.time())
        if now - self.last_update >= 1 or force:
            self.last_update = now
            
            self.msg = await self.msg.edit(content=self.__string)

    
    
    async def get_server_by_name(self, name: str, context: str = None) -> str:
        
        _ = await db.execute(
            "SELECT uuid FROM PTERODACTYL_SERVERS WHERE "
            f"`name` LIKE '%{name}%' LIMIT 1"
        )
        
        if context == 'KGB':
            if _ not in self.mc.tunables('KGB_SERVER_IDS').splitlines():
                raise ValueError(f"Server `{name}` not found in KGB server list")
        
        self.servers[_] = {'name': name}
        return _



    async def signal_server(self, signal: str, server_ids: list) -> None:
        
        if not isinstance(server_ids, list): raise TypeError("server_ids must be a list")
        
        await self.__msg(signal=signal)
        
        async with aiohttp.ClientSession() as session:
            
            for server_id in server_ids:
                await self.__signals(session, server_id=server_id, signal=signal)
                await self.__update_message()
            await self.__update_message(force=True)



    async def __signals(self, session: aiohttp.ClientSession, server_id: str, signal: str) -> None:
        
        # return
        
        url = f"{self.mc.tunables('PTERODACTYL_PANEL_URL')}/api/client/servers/{server_id}/power"

        headers = {
            'Authorization': f'Bearer {self.mc.tunables("PTERODACTYL_API_KEY")}',
            'Content-Type': 'application/json',
        }
        
        json_data = {
            'signal': signal
        }

        async with session.post(url, headers=headers, json=json_data) as response:
            
            if response.status == 204:
                self.__string = replace_line_in_string(
                    original_string=self.__string, 
                    search_criteria=self.servers[server_id]['name'],
                    new_line=f"{self.mc.tunables('SUCCESS_EMOJI')} · {self.servers[server_id]['name']}"
                )
            else:
                self.__string = replace_line_in_string(
                    original_string=self.__string, 
                    search_criteria=self.servers[server_id]['name'],
                    new_line=f"{self.mc.tunables('ERROR_EMOJI')} · {self.servers[server_id]['name']}"
                )