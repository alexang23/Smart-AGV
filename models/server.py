from database import Base
from sqlalchemy import Column, String, Boolean, Integer, DateTime
from dataclasses import dataclass
from sqlalchemy.sql import func


@dataclass
class RVServer(Base):
	__tablename__ = 'rv_server'

	name: str = Column(String(64), primary_key=True, unique=True, nullable=False)
	send_subject: str = Column(String(100), nullable=False)
	listen_subject: str = Column(String(100), nullable=False)
	rvs_enable: bool = Column(Boolean(), default=False, server_default='0', nullable=False)
	updated_at: str = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now(), onupdate=func.now())
 
@dataclass
class Server(Base):
	__tablename__ = 'server'

	name: str = Column(String(64), primary_key=True, unique=True, nullable=False)
	ip: str = Column(String(40), nullable=False)
	port: int = Column(Integer, nullable=False)
	url: str = Column(String(100), nullable=True)
	svr_enable: bool = Column(Boolean(), default=False, server_default='0', nullable=False)
	updated_at: str = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now(), onupdate=func.now())
	