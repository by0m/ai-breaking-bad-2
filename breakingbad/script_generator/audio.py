

import asyncio
import os
import uuid
import aiofiles
from pydub import AudioSegment
from pydub.utils import mediainfo
from pydub.effects import normalize, strip_silence

import pydub 

import aiohttp
from .asyncfakeyou import AsyncTTS
from ..database import Script, Line
import logging

logger = logging.getLogger("api")


MAX_AUDIO_LENGTH = 30000

pydub.AudioSegment.ffmpeg = f"./ffmpeg.exe"
 
class AudioGenerator:
    def __init__(self, username: str, password: str, voices: dict) -> None:
        self.username = username
        self.password = password
        self.voices = voices

    @classmethod
    async def create(self, username, password, voices):
        self = AudioGenerator(username, password, voices)

        self.fakeyou = AsyncTTS(self.username, self.password)
        await self.fakeyou.login(self.username, self.password)
        return self


    async def generate_line(self, line: Line, retries=3):
        if retries == 0:
            return 

        try:
            wav = await self.fakeyou.say(line.text, self.voices[line.name.strip()])
            
            async with aiohttp.ClientSession() as session:
                path = await self.download_audio(session, wav.link)
            
            self.fix_audio(path)

            logger.info(f"Created audio {line.name} - '{line.text}'")
        except Exception as err:
            logging.info(f"Line failed to generate {line}. Reason: {err}")
            return await self.generate_line(line, retries=retries - 1)

        return path
        
    def fix_audio(self, path):
        audio = AudioSegment.from_wav(path)

        bit_rate = mediainfo(path)["bit_rate"]

        audio = audio[:30000]
        
        audio = normalize(audio)

        audio += 6


        audio.export(path, format="wav", bitrate=bit_rate)




    async def generate(self, script: Script):
        tasks = []
        for line in script.lines:
            tasks.append(self.generate_line(line))

        return await asyncio.gather(*tasks)
    

    async def download_audio(self, session: aiohttp.ClientSession, link) -> str:

        path = os.path.abspath(f'audio/{uuid.uuid4()}.wav')

        async with session.get(link) as resp:
            if resp.status == 200:

                f = await aiofiles.open(path, mode='wb')

                await f.write(await resp.read())

                await f.close() 

        return path
    
 
    

