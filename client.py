import asyncio
from breakingbad import BreakingBad

import discord
from discord.ext import commands



intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

async def main():
    program = await BreakingBad.create(bot)

    await program.start() 

asyncio.run(main()) 
