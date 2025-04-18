from sqlalchemy import Column, BigInteger, Text, DateTime, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Guild(Base):
    """
    Represents a Discord guild with its associated Google Form attendance ID and URL.
    """
    __tablename__ = 'guilds'

    guild_id = Column(BigInteger, primary_key=True)
    form_url = Column(Text, nullable=True)
    
class Attendance(Base):
    """
    Records a user's attendance for a given guild.
    The primary key `id` corresponds to the guild's attendance_id from Guild.attendance_id.
    """
    __tablename__ = 'attendances'

    guild_id = Column(BigInteger, ForeignKey('guilds.guild_id', ondelete='CASCADE'), nullable=False)
    user_id = Column(BigInteger, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    form_url = Column(Text, nullable=True)

    # Composite primary key 
    __table_args__ = (
        PrimaryKeyConstraint('guild_id', 'user_id'),
    )
