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

    ip_address = Column(String, index=True)
    is_assigned = Column(Boolean, default=False)



async def async_populate_ip_pool(subnet: str):
    """Ensure database session before running population task"""
    async for session in get_session():
        await populate_ip_pool(session, subnet)
        break  # ✅ Ensure only one session is used


def after_create(target, connection, **kw):
    """Run `populate_ip_pool()` after `wireguard_ip_pool` is created."""
    subnet = os.getenv("ALLOWED_IPS")
    if not subnet:
        raise ValueError("ALLOWED_IPS environment variable is not set")
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(async_populate_ip_pool(subnet))  # ✅ Non-blocking execution
    else:
        loop.run_until_complete(async_populate_ip_pool(subnet))  # ✅ Ensure execution


# Register the event listener to populate IP pool after table creation
event.listen(WireGuardIPPool.__table__, "after_create", after_create)