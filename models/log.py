from database import Base
from sqlalchemy import Column, String, Integer, DateTime, Index
from sqlalchemy.sql import func
from dataclasses import dataclass

@dataclass
class Log(Base):
    __tablename__ = 'log'

    id: int = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    #commandID: str = Column(String(100), default='None', index=True)
    event: str = Column(String(50), default='SYSTEM', index=True, nullable=False)
    user: str = Column(String(100), nullable=False)
    message: str = Column(String(512), nullable=False)
    #trace: str = Column(String(4000), default='')
    #new: bool = Column(Boolean(), default=True, nullable=False)
    type: str = Column(String(24), default='INFO', server_default='INFO', nullable=False)
    created_at: str = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now(), onupdate=func.now())
    __table_args__ = (Index('ix_createdat_event','created_at', "event"),)