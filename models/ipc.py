from database import Base
from sqlalchemy import Column, String, Boolean, Integer, DateTime
from dataclasses import dataclass
from sqlalchemy.sql import func


@dataclass
class IPC(Base):
	__tablename__ = 'ipc'

	id: int = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
	device_id: str = Column(String(64), unique=True, nullable=False)
	name: str = Column(String(100), nullable=False)
	group: str = Column(String(100), nullable=True)
	ip: str = Column(String(40), nullable=False)
	port: int = Column(Integer, nullable=False)
	ipc_enable: bool = Column(Boolean(), default=True, server_default='1', nullable=False)
	ftp_enable: bool = Column(Boolean(), default=False, server_default='0', nullable=False)
	alarm_mode: int = Column(Integer, default=0, nullable=False)
	created_at: str = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now())
	updated_at: str = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now(), onupdate=func.now())
	