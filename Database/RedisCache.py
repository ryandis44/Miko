import asyncio
import os
import redis.asyncio as redis
from redis.commands.json.path import Path
from tunables import *
from Database.database_class import ip

connection = None
async def connect_redis():
    global connection
    
    try:
        print("\n\n[REDIS] Attempting local connection...")
        if os.getenv('CONNECTION') == "REMOTE": raise Exception
        connection = redis.Redis(
            host='192.168.0.12',
            port=6380,
            password=tunables('REDIS_PASSWORD'),
            decode_responses=True,
            socket_timeout=2
        )
        if not await connection.ping(): raise Exception
        
        print("[REDIS] Connected locally!")
    except Exception as e:
        print(f"[REDIS] Server not running locally. Attempting connection via Cloudflare...")
        try:
            connection = redis.Redis(
                host=ip,
                port=6380,
                password=tunables('REDIS_PASSWORD'),
                decode_responses=True
            )
            
            if not await connection.ping(): raise Exception
            
            print("[REDIS] Connected via Cloudflare!")
        except:
            print(f"\n##### [REDIS] FAILED TO CONNECT TO SERVER! #####\n{e}\n")


async def check_redis():
    global connection
    if connection is None:
        await connect_redis()
    try:
        if not await connection.ping(): raise Exception
    except: await connect_redis()

class RedisCache:
    
    def __init__(self, file):
        self.file = file
    
    async def set(self, key: str, value, type: str, path: str=".", p=False) -> bool:
        if p: print(
            f"> Key: {key}\n"
            f"> Value: {value}"
        )
        global connection
        for attempt in range(1,6):
            try:
                async with connection.pipeline(transaction=True) as pipe:
                    match type:
                        case "STRING": pipe.set(key, value)
                        case "JSON": pipe.json().set(key, path, value)
                    await pipe.execute()
            except Exception as e:
                if attempt < 5:
                    if os.getenv('DATABASE_DEBUG') != "1": await asyncio.sleep(5)
                    await check_redis()
                    continue
                else:
                    print(f"\n[REDIS] ERROR! [{self.file}] Could not SET VALUE: \"{key, value}\"\n{e}")
                    return False
            return True
    
    
    
    async def get(self, key: str, type: str):
        global connection
        # async with connection.pipeline(transaction=True) as pipe:
        try:
            match type:
                case "STRING": return await connection.get(key)
                case "JSON": return await connection.json().get(key)
        except Exception as e:
            print(f"[REDIS] Error retriving value from key {key}:\n{e}")
            return None
