import asyncio
from typing import Any
import discord
from discord import app_commands
from discord.flags import Intents
from discord.ext import commands
from datetime import datetime, timedelta

from ..database import Script, Database, Author
from ..script_generator import ScriptGenerator
from .classes import NoAccess, QueueEmbed, TopicEmbed, TopicList, TopicView

GUILD_ID = 1101592255111909540

CHANNEL_IDS = [1117172397288730644, 1117118458405073010, 1128419002297897083]

STREAM_ANNOUNCEMENTS = 1121156892811591760
LOGS = 1119372967265177710
REPORTS_CHANNEL = 1130533458196840519
notification_channel_id = 1149853014220345486

ROLES = {
    "mod" : 1118960480350916751, 
    "developer" : 1116864974439067788
}



class GusBot(commands.Cog):
    def __init__(self, bot: commands.Bot, database: Database, script_generator: ScriptGenerator) -> None:
        self.bot = bot  
        self.database = database
        self.script_generator = script_generator
        self.guild = discord.Object(GUILD_ID)
    
    

    @app_commands.command(name="topic", description="Adds a topic to the generation queue.")
    @app_commands.describe(topic="The topic you want the characters to discuss.", priority="Mod only")
    async def topic(self, interaction: discord.Interaction, topic: str, priority: bool = False):
        if not interaction.channel.id in CHANNEL_IDS:
            return await NoAccess.create(interaction, "Please use channel {}", channel=CHANNEL_IDS[0])
        
        if priority and not interaction.user.get_role(ROLES["mod"]):
            return await NoAccess.create(interaction, "Moderator is required to perform this command.")
        
        priority = int(priority)

        word_is_present, word = Script.contains_banned_word(topic)
        tempword_is_present, tempword = Script.contains_banned_word(topic, "./tempbanned_words.txt")
        if word_is_present:
            await interaction.user.timeout(datetime.now().astimezone() + timedelta(days=1), reason=f'Submited topic with word {word}')
            embed = discord.Embed(title='Logs', description=f'Timed out user {interaction.user.mention} for a day.\nReason:\nSubmited topic with word```{word}```')
            await self.bot.get_channel(LOGS).send(embed=embed)
            embed = discord.Embed(title="Timed Out", description=f'Do not include slurs in your topics, You have been timed out, If you think this is a mistake then please contact a mod.')
            await interaction.response.send_message(embed= embed)
            return
        elif tempword_is_present:
            embed = discord.Embed(title="🤓", description=f'```{tempword}``` is banned')
            await interaction.response.send_message(embed= embed)
            await interaction.user.timeout(datetime.now().astimezone() + timedelta(minutes=1), reason=f'Submited topic with word {word}')
            embed = discord.Embed(title='Logs', description=f'Warned user {interaction.user.mention}.\nReason:\nSubmited topic with word```{tempword}```')
            await self.bot.get_channel(LOGS).send(embed=embed)
            return


        topic_embed = TopicEmbed(topic)
        topic_embed.add_generation_field("script")
        topic_embed.add_generation_field("audio")

        topic_view = TopicView(topic_embed, interaction)


        await interaction.response.send_message(embed=topic_embed, view=topic_view)

        message = await interaction.original_response()

        author = Author(interaction.user.id, interaction.user.name, "discord")

        script = await self.script_generator.generate(topic, author, priority=priority)

        if not script:
            topic_embed.fail()

            await message.edit(embed=topic_embed)

            return

        else:
            topic_embed.success("script", f"- id {script.id}")

            await message.edit(embed=topic_embed)

       

        while script.created is False and script.used is False:
            await asyncio.sleep(5)
            async with self.database.session() as session:
                script: Script = await session.get(Script, script.id)
                
        topic_embed.success("audio")
        await message.edit(embed=topic_embed)
        
        while script.used is False:
            await asyncio.sleep(5)
            async with self.database.session() as session:
                script: Script = await session.get(Script, script.id)


        if topic_view.notifications is False:
            await topic_view.stop()
            return

        embed = discord.Embed(title='Notification', description=f'Your prompt ```{script.topic}``` is about to play!\nYou can view it in <#{STREAM_ANNOUNCEMENTS}>', colour=discord.Colour.green()) 
        notification_channel = self.bot.get_channel(notification_channel_id)
        if notification_channel:
            await notification_channel.send(content=f'<@{author.id}>', embed=embed)


    @app_commands.command(name="queuedelete", description="Allows a mod to delete an item in the queue")
    @app_commands.describe(id="Id of prompt")
    async def queuedelete(self, interaction: discord.Interaction, id: int=None, user: discord.User=None):
        if not interaction.user.get_role(ROLES["mod"]):
            return await NoAccess.create(interaction, "Moderator is required to perform this command.")
        
        if not id and not user:
            return await NoAccess.create(interaction, "You must specify either an id or user!")
        
        async with self.database.session() as session:
            if id:

                script: Script = await session.get(Script, id)

                script.used = True
                script.created = True
                await session.commit()

                await session.refresh(script, ['author'])

                await interaction.response.send_message(f"Successfuly deleted item id - {script.id} - '{script.topic}' by '{script.author.name}'")

            elif user:
                
                author = await session.get(Author, user.id)
                

                if author is None:
                    return await NoAccess.create(interaction, f"Author '{user.name}' hasn't created any scripts!")
                
                await session.refresh(author, ['scripts'])
                
                if len(author.scripts) == 0:
                    return await NoAccess.create(interaction, f"Author has no scripts in queue!")
                
                msg = ""
                for script in author.scripts:
                    await session.refresh(script)
                    if not script.used or not script.created:
                        
                        script.used = True
                        script.created = True
                        await session.commit()
                        msg += f"Successfuly deleted item id - {script.id} - '{script.topic}' by '{author}'\n"

                await interaction.response.send_message(msg)


    @app_commands.command(name="queue", description="Allows a user to view the queue.")
    async def queue(self, interaction: discord.Interaction):
        if not interaction.channel.id in CHANNEL_IDS:
            return await NoAccess.create(interaction, "Please use channel {}", channel=CHANNEL_IDS[0])

        
        view = QueueEmbed(interaction, self.database)

        embed = await view.create_embed()        
        
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

        await asyncio.sleep(180)

        await view.stop()

    @app_commands.command(name="report", description="Allows you to report a user who is spamming queue / using slurs")
    @app_commands.describe(user='User to report to mods.', reason="Why you are reporting the user")
    async def report(self, interaction: discord.Interaction, user: discord.User, reason: str):
        reports_channel = self.bot.get_channel(REPORTS_CHANNEL)
        async with self.database.session() as session:
            print(user.id)
            reported = await session.get(Author, user.id)

        if not reported:
            return await NoAccess.create(interaction, "User hasn't submitted any topics.")
        
        embed = discord.Embed(title='Report', description=f"User {user.mention} ({user.name}) was reported.")
        embed.set_author(name=f'Report by {interaction.user.name}', icon_url=interaction.user.avatar.url)
        embed.add_field(name='Reason', value=reason)

        topic_list = TopicList(interaction=None, author=reported, database=self.database)
        topic_embed = await topic_list.create_embed()

        await reports_channel.send(content=f"<@&{ROLES['mod']}>", embed=embed)
        await reports_channel.send(embed=topic_embed, view=topic_list)
        
        success_embed = discord.Embed(title="Success", description=f'User successfully reported', colour=discord.Colour.green())
        success_embed.set_author(name=f'{user.mention} reported.', icon_url=user.avatar.url)

        await interaction.response.send_message(embed=success_embed, ephemeral=True)



    @app_commands.command(name="showscript", description="Displays the content of a script.")
    @app_commands.describe(id="Id of prompt")
    async def showscript(self, interaction: discord.Interaction, id: int):
        if not interaction.user.get_role(ROLES["mod"]):
            return await NoAccess.create(interaction, "Moderator is required to perform this command.")
        
        
        async with self.database.session() as session:

            script: Script = await session.get(Script, id)

            await session.refresh(script, ["lines"])

        print(script.lines)

        showsscript_embed= discord.Embed(title="Script", description=script.topic, color=0xff0000)

        for i,line in enumerate(script.lines):
            showsscript_embed.add_field(name=f"{i + 1}. {line.name}", value=line.text, inline=False)

        await interaction.response.send_message(embed=showsscript_embed)

    @app_commands.command(name="clearqueue", description="Clears the queue.")
    async def clearqueue(self, interaction: discord.Interaction):
        if not interaction.user.get_role(ROLES['developer']):
            return await NoAccess.create(interaction, 'Developer only.')
        
        async with self.database.session() as session:
            scripts = await self.database.get_queue(session)

            for script in scripts:
                script.used = True
                script.created = True

            await session.commit()

        await interaction.response.send_message(f'Cleared {len(scripts)} scripts.')

        
    @commands.Cog.listener()
    async def on_ready(self):
        print("Started")

    @commands.command()
    async def sync(self, ctx: commands.Context):
        if not ctx.author.get_role(ROLES['developer']):
            return
        
        fmt = await self.bot.tree.sync()
        await ctx.send(f"Synced {len(fmt)} commands successfully!")
        
       

        
    @app_commands.command(name="viewtopics", description="View all the topics a user has submitted.")
    async def viewtopics(self, interaction: discord.Interaction, user: discord.User):
        async with self.database.session() as session:
            print(user.id)
            author = await session.get(Author, user.id)

        if not author:
            return await NoAccess.create(interaction, "User hasn't submitted any topics.")


        topic_list = TopicList(interaction, author=author, database=self.database)

        embed = await topic_list.create_embed()


        await interaction.response.send_message(embed=embed, view=topic_list)