from sqlalchemy import Column, Integer, String
from app.core.database import Base


class WGServerConfig(Base):
    __tablename__ = 'wg_server_config'


    server_name = Column(String(100),unique=True, nullable=False)
    address = Column(String(100),unique=True, nullable=False)
    listen_port = Column(Integer,unique=True, nullable=False)
    private_key = Column(String(100),unique=True, nullable=False)
    public_key = Column(String(100),unique=True, nullable=False)

