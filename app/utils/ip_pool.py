from app.logs.logging import logger
from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from ipaddress import IPv4Network



async def populate_ip_pool(db: AsyncSession, subnet: str):
    from app.api.peers.models import WireGuardIPPool
    """Populate the database with all available IPs from the subnet."""

    # Check if the table already contains the values matching the subnet length
    existing_ips_count = await db.scalar(select(func.count()).select_from(WireGuardIPPool))
    subnet_ips_count = len(list(IPv4Network(subnet).hosts())) - 1  # Exclude the first IP

    if existing_ips_count >= subnet_ips_count:
        logger.info("IP Pool already populated")
        return

    # Exclude the first IP (e.g., 10.8.0.1) as it's usually the gateway
    ip_list = [str(ip) for ip in IPv4Network(subnet).hosts()][1:]

    # Insert into database if not already populated
    for ip in ip_list:
        result = await db.execute(select(WireGuardIPPool).where(WireGuardIPPool.ip_address == ip))
        if not result.scalars().first():
            db.add(WireGuardIPPool(ip_address=ip, is_assigned=False))

    logger.info("IP Pool populated")

    await db.commit()


async def get_next_available_ip(db: AsyncSession, ip: str = None) -> str:
    from app.api.peers.models import WireGuardIPPool

    """Retrieve a specific unassigned IP if provided, otherwise get the next available IP."""

    if ip:
        # Check if the provided IP is available
        result = await db.execute(
            select(WireGuardIPPool).where(
                WireGuardIPPool.ip_address == ip, 
                WireGuardIPPool.is_assigned == False
            ).limit(1).with_for_update()
        )
    else:
        # Select the next available IP
        result = await db.execute(
            select(WireGuardIPPool).where(
                WireGuardIPPool.is_assigned == False
            ).limit(1).with_for_update()
        )
    available_ip = result.scalars().first()
    if not available_ip:
        raise HTTPException(status_code=400, detail="No available IPs left or provided IP is already assigned")
    # Mark the IP as assigned
    await db.execute(
        update(WireGuardIPPool)
        .where(WireGuardIPPool.ip_address == available_ip.ip_address)
        .values(is_assigned=True)
    )

    await db.commit()  # Ensure the change is committed

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
