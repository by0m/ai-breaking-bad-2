import asyncio
import discord
from sqlalchemy import and_, desc, select
from .classes import *
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
import logging 

logger = logging.getLogger('database')


class Database:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.engine = None
        self.session = None

    async def __aenter__(self):
        self.engine = create_async_engine(self.database_url, echo=False)
        self.session = async_sessionmaker(self.engine, expire_on_commit=False)

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database started.")

        return self

    async def __aexit__(self, *err):
        await self.engine.dispose()

    async def get_uncreated_audios(self, session: AsyncSession) -> Script:
        result = await session.scalars(
            select(Script).filter(and_(Script.created == False, Script.used == False)).order_by(desc(Script.priority))
        )
        
        script = result.first()

        if script:
            logger.info(f"Found uncreated script {script}.")
            await session.refresh(script, ["lines"])
            return script





    async def add(self, session: AsyncSession, obj):

        session.add(obj)
        await session.commit()

    async def get_unused(self, session: AsyncSession):
        result = await session.scalars(
            select(Script).filter(and_(Script.created == True, Script.used == False)).order_by(desc(Script.priority))
        )
        
        script = result.first()

        if script:
            logger.info(f"Found uncreated script {script}.")
            await session.refresh(script, ["lines"])
            return script
       

    async def get_queue(self, session: AsyncSession) -> list[Script]:
        result = await session.scalars(
            select(Script).filter(Script.used == False).order_by(desc(Script.priority))
        )

        scripts = result.all()


        
        logger.debug(f"Got queue {scripts[:5]}")
        return scripts
    
    async def get_donations(self, session: AsyncSession) -> list[Script]:
        return (await session.scalars(select(Donation))).all()
    

    async def create_or_get_author(self, session: AsyncSession, author_obj: Author):
        author = await session.get(Author, author_obj.id)

        if author is None:
            session.add(author_obj)
            author = author_obj

        return author
