# Copyright (c) 2025 WilsonnnTan. All Rights Reserved.
"""
SQLAlchemy ORM models for the Discord Attendance Bot database schema.
Defines tables for guild configuration, attendance records, and timezone settings.
"""
from sqlalchemy import Column, BigInteger, Text, DateTime, ForeignKey, PrimaryKeyConstraint, UniqueConstraint, Integer
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Guild(Base):
    """
    SQLAlchemy model for a Discord guild (server).
    Stores Google Form URL and attendance window configuration for each guild.
    """
    __tablename__ = 'guilds'
    __table_args__ = (
        UniqueConstraint('guild_id', name='uq_guilds_guild_id'),
    )

    guild_id = Column(BigInteger, primary_key=True)
    form_url = Column(Text, nullable=True)
    day = Column(Integer, nullable=True)  # Day of the week for attendance (1=Monday, 7=Sunday)
    start_hour = Column(Integer, nullable=True)
    start_minute = Column(Integer, nullable=True)
    end_hour = Column(Integer, nullable=True)
    end_minute = Column(Integer, nullable=True)

class Attendance(Base):
    """
    SQLAlchemy model for attendance records.
    Tracks when a user marks attendance in a given guild.
    Composite primary key: (guild_id, user_id).
    """
    __tablename__ = 'attendances'
    __table_args__ = (
        PrimaryKeyConstraint('guild_id', 'user_id', name='pk_attendances'),
    )

    guild_id = Column(BigInteger, ForeignKey('guilds.guild_id', ondelete='CASCADE'), nullable=False)
    user_id = Column(BigInteger, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    form_url = Column(Text, nullable=True)

class Timezone(Base):
    """
    SQLAlchemy model for storing timezone offset per guild.
    """
    __tablename__ = 'Timezone'
    __table_args__ = (
        UniqueConstraint('guild_id', name='uq_timezone_guild_id'),
    )

    guild_id = Column(BigInteger, ForeignKey('guilds.guild_id', ondelete='CASCADE'), primary_key=True)
    time_delta = Column(Integer, nullable=True)