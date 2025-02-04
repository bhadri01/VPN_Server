import select
import subprocess
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ipaddress import IPv4Network

from app.api.peers.models import WireGuardPeer


# Define your WireGuard subnet (Change as per your network setup)
WIREGUARD_SUBNET = "10.0.0.0/24"


async def get_next_available_ip(db: AsyncSession) -> str:
    """Find the next available IP in the WireGuard subnet"""
    subnet = IPv4Network(WIREGUARD_SUBNET)
    
    # Query database for existing assigned IPs
    result = await db.execute(select(WireGuardPeer.assigned_ip))
    assigned_ips = {row[0] for row in result.fetchall()}

    # Find the first available IP in the range
    for ip in subnet.hosts():
        ip_str = str(ip)
        if ip_str not in assigned_ips:  # Check if IP is already assigned
            return ip_str

    raise HTTPException(status_code=400, detail="No available IP addresses left")

def generate_wg_key_pair() -> tuple[str, str]:
    """Generates a WireGuard key pair (private key & public key)"""
    
    # Generate private key
    private_key = subprocess.check_output("wg genkey", shell=True).decode().strip()

    # Generate public key from private key
    public_key = subprocess.check_output(f"echo {private_key} | wg pubkey", shell=True).decode().strip()
    
    return private_key, public_key