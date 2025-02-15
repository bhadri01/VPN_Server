import os
from httpx import get
from sqlalchemy import Boolean, Column, ForeignKey, String,event
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


class WireGuardIPPool(Base):
    __tablename__ = "wireguard_ip_pool"

    ip_address = Column(String, primary_key=True, index=True)
    is_assigned = Column(Boolean, default=False)


def after_create(target, connection, **kw):
    """Wrap the async function inside an event listener"""
    
    async def async_populate():
        # Use async for to extract session from async generator
        async for session in get_session():
            await populate_ip_pool(session)

    loop = asyncio.get_event_loop()
    
    if loop.is_running():
        asyncio.create_task(async_populate())  # Schedule the async function
    else:
        loop.run_until_complete(async_populate())

# Register the event listener for after_create
event.listen(WireGuardIPPool.__table__, "after_create", after_create)