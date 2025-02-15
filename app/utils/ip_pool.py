from app.logs.logging import logger
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ipaddress import IPv4Network



async def populate_ip_pool(db: AsyncSession, subnet: str = "10.0.0.0/24"):
    from app.api.peers.models import WireGuardIPPool
    """Populate the database with all available IPs from the subnet."""

    # Exclude the first IP (e.g., 10.8.0.1) as it's usually the gateway
    ip_list = [str(ip) for ip in IPv4Network(subnet).hosts()][1:]

    # Insert into database if not already populated
    for ip in ip_list:
        result = await db.execute(select(WireGuardIPPool).where(WireGuardIPPool.ip_address == ip))
        if not result.scalars().first():
            db.add(WireGuardIPPool(ip_address=ip, is_assigned=False))

    logger.info("IP Pool populated")

    await db.commit()


async def get_next_available_ip(db: AsyncSession) -> str:
    from app.api.peers.models import WireGuardIPPool

    """Retrieve the next unassigned IP from the database."""

    result = await db.execute(
        select(WireGuardIPPool).where(
            WireGuardIPPool.is_assigned == False).limit(1)
    )

    available_ip = result.scalars().first()

    if not available_ip:
        raise HTTPException(status_code=400, detail="No available IPs left")

    # Mark the IP as assigned
    available_ip.is_assigned = True
    await db.commit()

    return available_ip.ip_address


async def release_ip(db: AsyncSession, ip: str):
    from app.api.peers.models import WireGuardIPPool

    """Mark an IP as available when a peer is deleted."""
    result = await db.execute(
        select(WireGuardIPPool).where(WireGuardIPPool.ip_address == ip)
    )

    ip_entry = result.scalars().first()
    if ip_entry:
        ip_entry.is_assigned = False
        await db.commit()
