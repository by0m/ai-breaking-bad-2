
import asyncio
import functools
import aiohttp
from discord.ext import commands

from .streamElements import DonationHandler

from .discordbot.bot import GusBot
from .database import Database, Script, Line, Donation, Author
from .script_generator import ScriptGenerator, AudioGenerator
import logging

from .credentials import openai, FakeYou, StreamElements, Discord


logger = logging.getLogger('api')

VOICES = {
    "Gustavo" : "TM:49yn4v5671zq",
    "Mike" : "TM:vjmcch54xa2y",
    "Saul" : "TM:b8efnnxdx14m",
    "Walter" : "TM:8afk285jc2gs",
    "Jesse" : "TM:dznwvyadj7zm",
    "Hank" : "TM:fvhe1wz4tm33"
}

DATABASE_URL = "sqlite+aiosqlite:///topics.sqlite"

def forever_loop(time_delay: int):
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            while not await asyncio.sleep(time_delay):
                try:
                    await func(*args, **kwargs)
                except Exception as err:
                    logger.exception(err, stack_info=True)
        return wrapped
    return wrapper



class BreakingBad:
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        
    @classmethod
    async def create(self, bot: commands.Bot):
        self = BreakingBad(bot)
        self.database = await Database(DATABASE_URL).__aenter__()
        self.script_generator = ScriptGenerator(self.database, voices=VOICES, apikey=openai.apikey)
        self.audio_generator = await AudioGenerator.create(FakeYou.username, FakeYou.password, voices=VOICES)

        gusbot = GusBot(bot, self.database, self.script_generator)
        await self.bot.add_cog(gusbot)

        return self


    async def start(self):
        
        await asyncio.gather(self.bot.start(Discord.TOKEN), self.audio_creator(), self.donation_handler())

    

    @forever_loop(time_delay=1)
    async def audio_creator(self):
        
        async with self.database.session() as session:
            script = await self.database.get_uncreated_audios(session)

            if not script:
                return

            logger.info(f"Generating audio for {script} - id - {script.id}")

            audio_paths = await self.audio_generator.generate(script)

            failed = None in audio_paths

            for line, audio_path in zip(script.lines, audio_paths):
                line.audio = audio_path

            if failed:
                script.used = True

            script.created = True
            await session.commit()

            logger.info(f"Generation complete  for {script} - id - {script.id} - failed {failed}")

    

    @forever_loop(time_delay=5)
    async def donation_handler(self):
    
        money = DonationHandler(jwt_token=StreamElements.JWT, channel_id=StreamElements.CHANNEL_ID)
        
        async with self.database.session() as session:        
            donations = await money.get_tips()

            results = await self.database.get_donations(session)
            ids = [result.id for result in results]

            tasks = []
            
            for donation in donations:
                if donation.id in ids:
                    continue
                
                await self.database.add(session, donation)

                author = Author(donation.id, donation.username, "donation")


                tasks.append(self.script_generator.generate(donation.text, author, priority=1, length=30))

            await asyncio.gather(*tasks)

                        
    @forever_loop(time_delay=10)
    async def nightbot_handler(self):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://breakinggoodaicontrol.azurewebsites.net/ztopicrecommendation") as resp:
                await asyncio.gather(*[self.script_generator.generate(script.get("topic"), script.get("username")) for script in await resp.json()])
  
