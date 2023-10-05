import datetime
from typing import Any, Optional, Union
import discord
from discord.colour import Colour
from discord.types.embed import EmbedType
from sqlalchemy import select

from ..database import Script, Database, Author
from sqlalchemy.ext.asyncio import AsyncSession

from breakingbad.script_generator import ScriptGenerator

LOADING_EMOJI = "<a:loading:1119969904301449307>"


class NoAccess:
    def __init__(self, interaction: discord.Interaction, msg="You can't do that!", channel: int = None) -> None:
        self.interaction = interaction

        
    @classmethod
    async def create(self, interaction: discord.Interaction, msg="You can't do that!", channel: int = None):
        self = NoAccess(interaction, msg, channel)

        if channel:
            msg = msg.format(interaction.guild.get_channel(channel).mention)

        await self.interaction.response.send_message(msg, ephemeral=True)

class ViewBase(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, timeout: float | None = 180):
        super().__init__(timeout=timeout)

        self.interaction = interaction

    async def stop(self) -> None:
        
        for item in self.children:
            item.disabled = True

        await self.interaction.edit_original_response(view=self)

    


class ListView(ViewBase):
    def __init__(self, interaction: discord.Interaction[discord.Client], timeout: float | None = 180):
        super().__init__(interaction, timeout)

        self.pos = 0
        self.list_items = []

    @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.blurple)
    async def backwards(self, interaction: discord.Interaction, button: discord.Button):
        if not self.pos == 0:
            self.pos -= 10

        self.interaction = interaction
        
        embed = await self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)


    @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.blurple)
    async def forwards(self, interaction: discord.Interaction, button: discord.Button):
        embed = await self.create_embed()

        if not self.pos + 10 >= len(self.list_items):
            self.pos += 10
            
        self.interaction = interaction
        
        await interaction.response.edit_message(embed=embed, view=self)

    async def update_list(self):
        raise ValueError("Must add a list update function!")
    async def create_embed(self):
        raise ValueError("Must add a response!")
            
    
            

class QueueEmbed(ListView):
    def __init__(self, interaction: discord.Interaction, database: Database, *, timeout: float | None = 180, ):
        super().__init__(interaction=interaction, timeout=timeout)   
        self.database = database
        


    async def create_embed(self):
        
        async with self.database.session() as session:
            await self.update_list(session)

            title = "Queue"
            description = f"There is {len(self.list_items)} scripts currently in queue."

            queue_embed=discord.Embed(title=title, description=description, color=0xff0000)

            for script in self.list_items[self.pos: 10 + self.pos]:
                await session.refresh(script, ["author"])

                pos = self.list_items.index(script)
                queue_embed.add_field(name=f"{pos}. {script.topic[:200].capitalize()}" ,value=f"id - {script.id} - author - {script.author.name}", inline= False)

            return queue_embed
        
    async def update_list(self, session):

        self.list_items = await self.database.get_queue(session)


class TopicEmbed(discord.Embed):
    title = "Topic generating"
    description = "Your prompt \n```{topic}```\n has been added to the queue! This message will update you on the progess of your prompt."  

    IN_PROGESS = f"Generating... {LOADING_EMOJI}"

    SUCCESS = "{} generated successfully! ✅"
    FAILED = "Failed to generate {}. ❌"


    
    def __init__(self, topic: str, priority=False,  *args, **kwargs):
        self.description = self.description.format(topic=topic)
        

        self.generation_fields = {}
        
        super().__init__(title=self.title, description=self.description, *args, **kwargs)

        

    def add_generation_field(self, name: str):
        self.add_field(name=f"{name.capitalize()} generation status:", value=self.IN_PROGESS, inline= False)
        
        self.generation_fields[name] = len(self._fields) - 1

    def fail(self):
        for key, value in self.generation_fields.items():

            self._fields[value]["value"] = self.FAILED.format(key)

    def success(self, name: str, extra_str=""):
        self._fields[self.generation_fields[name]]["value"] = f"{self.SUCCESS.format(name.capitalize())} {extra_str}"

    

class TopicView(ViewBase):
    def __init__(self, topic_embed: TopicEmbed, interaction: discord.Interaction, *, timeout: float | None = 180,):
        super().__init__(interaction=interaction, timeout=timeout)
        self.interaction = interaction
        self.topic_embed = topic_embed
        self.notifications = False
       
    
    @discord.ui.button(emoji="🔔", style=discord.ButtonStyle.blurple)
    async def notify(self, interaction: discord.Interaction, *args):
        if interaction.user.id != self.interaction.user.id:
            return await NoAccess.create(interaction, "You can only turn on notifications for your own prompt.")
        
        self.topic_embed.add_field(name = "Notifications", value="Prompt notifications have been enabled. You will be pinged when your prompt is about to play.", inline=False)
        await interaction.response.edit_message(embed=self.topic_embed, view=self)

        self.notifications = True

        await self.stop()

        
class TopicList(ListView):
    def __init__(self, interaction: discord.Interaction, author: Author, database: Database):
        super().__init__(interaction, 180)

        self.database = database
        self.author = author

    async def update_list(self, session: AsyncSession):
        
            
        session.add(self.author)
        await session.refresh(self.author, ["scripts"])
        print(self.author.scripts)

        self.list_items = self.author.scripts

    async def create_embed(self):
        async with self.database.session() as session: 
            await self.update_list(session)
            title = "Topics"
            description = f"{self.author.name} has created {len(self.author.scripts)} scripts."

            queue_embed=discord.Embed(title=title, description=description, color=discord.Colour.blue())

            for script in self.list_items[self.pos: 10 + self.pos]:
                await session.refresh(script, ["topic"])

                pos = self.list_items.index(script)
                queue_embed.add_field(name=f"Id - {script.id}" ,value=f"{script.topic[:1000]} ", inline= False)

            return queue_embed
        
