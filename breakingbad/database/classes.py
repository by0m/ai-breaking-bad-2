from dateutil.parser import parse
from typing import Any
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs
import logging

logger = logging.getLogger('database')

class Base(AsyncAttrs, DeclarativeBase):
    pass

class Author(Base):
    __tablename__ = 'author'

    id = Column(String, primary_key=True)
    name = Column(String)
    platform = Column(String)
    scripts = relationship("Script", back_populates="author")

    def __init__(self, id: int, name: str, platform = str):
        self.id = id
        self.name = name
        self.platform = platform

    def __repr__(self) -> str:
        return self.name


class Script(Base):
    __tablename__ = "script"

    id = Column(Integer, primary_key=True)
    topic = Column(String)
    prompt = Column(String)
    created = Column(Boolean)
    used = Column(Boolean)
    priority = Column(Integer)
    author_id = Column(Integer, ForeignKey('author.id'))
    author = relationship("Author", back_populates="scripts")
    lines = relationship("Line", back_populates="script")
    
    def __init__(self, topic: str, prompt: str, author: Author, created=False, used=False, priority=0):
        self.topic = topic
        self.created = created
        self.used = used
        self.prompt = prompt
        self.author = author
        self.priority = priority



        logger.info(f"Created record Script {self}.")


    def __repr__(self) -> str:
        return f"<Script topic='{self.topic}'>"
    
    @staticmethod
    def contains_banned_word(topic, filename="./banned_words.txt"):
        with open(filename, "r") as file:
            for word in file.readlines():
                if word.strip() in topic.lower():
                    return True, word
                
        return False, None
    
    


class Line(Base):
    __tablename__ = "line"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    text = Column(String)
    audio = Column(String)


    script_id = Column(Integer, ForeignKey('script.id'))
    script = relationship("Script", back_populates="lines")

    def __init__(self, name: str, text: str, script: Script,  audio=""):
        self.name = name
        self.text = text
        self.audio = audio
        self.script = script

        logger.debug(f"Created record Line {self}.")


    def dictionary(self):
        json_line = {
            "name": self.name,
            "text": self.text,
            "audio": self.audio
        }

        logger.debug(f"Converted line {self} to dict.")

        return json_line

    def __repr__(self) -> str:
        return f"<Line text='{self.text}'>"
    


class Donation(Base):
    __tablename__ = "donation"
    
    id = Column(String, primary_key=True)
    username = Column(String)
    text = Column(String)
    email = Column(String)
    donation_amount = Column(Integer)
    date = Column(DateTime)

    def __init__(self, id: str, username: str, text: str, email: str, donation_amount: int, isodate: str):
        self.id = id
        self.username = username
        self.text = text
        self.email = email
        self.donation_amount = donation_amount
        self.date = parse(isodate)




