from functools import partial
import os
from httpx import get
from sqlalchemy import Boolean, Column, ForeignKey, String,event   
from sqlalchemy.orm import relationship
from app.core.database import Base, get_session
from app.utils.ip_pool import populate_ip_pool
import asyncio


class WireGuardPeer(Base):

    __tablename__ = "wireguard_peers"
    user_id = Column(String, ForeignKey("users.id"))
    peer_name = Column(String, index=True)
    public_key = Column(String, unique=True, index=True)
    private_key = Column(String, unique=True, index=True)
    assigned_ip = Column(String, unique=True, index=True)
    server_id = Column(String, ForeignKey("wg_server_config.id"))

    wg_server = relationship("WGServerConfig", back_populates="peers")


class WireGuardIPPool(Base):
    __tablename__ = "wireguard_ip_pool"

    ip_address = Column(String, primary_key=True, index=True)
    is_assigned = Column(Boolean, default=False)

