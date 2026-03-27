from database import Base
from sqlalchemy import Column, String, Boolean, Integer, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from dataclasses import dataclass

@dataclass
class SECS(Base):
    __tablename__ = 'secs'
    __table_args__ = (UniqueConstraint("sf", "code", "subcode", name="uc_sf_code_subcode"),)
    id: int = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    sf: str = Column(String(32), nullable=False)
    code: str = Column(Integer, nullable=False)
    subcode: str = Column(Integer, default=0x0000, nullable=False)
    msgtext: str = Column(String(256), nullable=False)
    description: str = Column(String(512), default='', server_default='', nullable=True)
    created_at: str = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now())
    updated_at: str = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now(), onupdate=func.now())
    argp: bool = Column(Boolean(), default=False, server_default='0', nullable=False)
    ens: bool = Column(Boolean(), default=False, server_default='0', nullable=False)
    eqas: bool = Column(Boolean(), default=False, server_default='0', nullable=False)
    webapi: bool = Column(Boolean(), default=False, server_default='0', nullable=False)
    ftp: bool = Column(Boolean(), default=False, server_default='0', nullable=False) 
