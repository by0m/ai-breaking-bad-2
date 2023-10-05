import asyncio
import json
from uuid import uuid4
from fakeyou.asynchronous_fakeyou import AsyncFakeYou
from fakeyou.exception import RequestError

import aiohttp,json,time,asyncio,re
from uuid import uuid4
from fakeyou.objects import *
from fakeyou.exception import *
import logging 

logger = logging.getLogger('api')


class AsyncTTS(AsyncFakeYou):
    def __init__(self, username, password, verbose: bool = False):
        self.username = username
        self.password = password

        super().__init__(verbose)
    
    async def make_tts_job(self,text:str,ttsModelToken:str,filename:str="fakeyou.wav"):
        
        if self.v:
            print("getting job token")

        payload={"uuid_idempotency_token":str(uuid4()),"tts_model_token":ttsModelToken,"inference_text":text}
        async with self.session.post(url=self.baseurl+"tts/inference",data=json.dumps(payload)) as handler:
			
            if handler.status==200:
                aijt=await handler.json()
                ijt= aijt["inference_job_token"]
                return ijt
            


            elif handler.status==429:
                await asyncio.sleep(5)
                return await self.make_tts_job(text,ttsModelToken,filename)
            
            elif handler.status == 400:
                handler.raise_for_status()

            else:
                logger.info(f"no friends {handler.status} '{text}'")
                await asyncio.sleep(1)
                return await self.make_tts_job(text,ttsModelToken,filename)
            
            
            
    async def tts_poll(self,ijt:str):
        if ijt == None:
            return
        for i in range(100):
            await asyncio.sleep(1)
            async with self.session.get(url=self.baseurl+f"tts/job/{ijt}") as handler:
                if handler.status==200:
                    hjson=await handler.json()
                    wavo=wav(hjson)
                    if self.v:
                        print("WAV STATUS :",wavo.status)

                    if wavo.status=="started":
                        continue
                    elif "pending" == wavo.status:
                        continue
                    elif "attempt_failed" == wavo.status:
                        raise Failed()
                    
                    elif "dead" == wavo.status:
                        raise Dead()
                    
                    elif "complete_success" == wavo.status:
                        if wavo.link != None:
                            async with self.session.get(wavo.link) as rcontent:
                                del wavo
                                #for RAM
                                
                                return wav(hjson,rcontent)
                        else:
                            raise PathNullError()
                elif handler.status==429:
                    raise TooManyRequests("Too many requests, try again later")
            

    