import asyncio
from ipaddress import IPv4Network
import os
import stat
import subprocess
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.peers.models import WireGuardPeer
from app.api.users.models import AuditLog
from app.utils.ip_check import generate_wg_key_pair, get_next_available_ip

WIREGUARD_SUBNET = "10.0.0.0/24"


class peer_service:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    async def log_action(admin_username, action, target, db: AsyncSession):
        log_entry = AuditLog(admin_username=admin_username,
                             action=action, target=target)
        db.add(log_entry)
        await db.commit()

# Define your WireGuard subnet (Change as per your network setup)

    @staticmethod
    async def get_next_available_ip(db: AsyncSession) -> str:
        """Find the next available IP in the WireGuard subnet"""
        subnet = IPv4Network(WIREGUARD_SUBNET)

        # Query database for existing assigned IPs
        result = await db.execute(select(WireGuardPeer.assigned_ip))
        assigned_ips = {row[0] for row in result.scalars().all()}

        # Find the first available IP in the range
        for ip in subnet.hosts():
            ip_str = str(ip)
            if ip_str not in assigned_ips:  # Check if IP is already assigned
                return ip_str

        raise HTTPException(
            status_code=400, detail="No available IP addresses left")

    @staticmethod
    def generate_wg_key_pair() -> tuple[str, str]:
        """Generates a WireGuard key pair (private key & public key)"""

        # Generate private key
        private_key = subprocess.check_output(
            "wg genkey", shell=True).decode().strip()

        # Generate public key from private key
        public_key = subprocess.check_output(
            f"echo {private_key} | wg pubkey", shell=True).decode().strip()

        return private_key, public_key


    async def get_all_peers(self):
        query = await self.db.execute(select(WireGuardPeer))
        result = query.scalars().all()
        return result


    async def add_peer(self, data, current_user):
        assigned_ip = await self.get_next_available_ip(self.db)
        private_key, public_key = self.generate_wg_key_pair()

        new_peer = WireGuardPeer(user_id=data.user_id, peer_name=data.peer_name,
                                 public_key=public_key, assigned_ip=assigned_ip)

        self.db.add(new_peer)

        command = f"wg set wg0 peer {public_key} allowed-ips {assigned_ip}/32"
        process = await asyncio.create_subprocess_shell(command)
        await process.communicate()  # Ensure command execution completes

        # Log action in the database
        await self.log_action(current_user.username, "Added peer", data.peer_name, self.db)

        return {"message": "Peer Created Successfully"}
    
    async def remove_peer(self,data,current_user):
        peer = await self.db.execute(select(WireGuardPeer).where(WireGuardPeer.id == data.peer_id))
        result = peer.scalars().first()
        
        if not result:
            raise HTTPException(
                detail={"Peer Not Found"},status_code=404
            )
        
        command = f"wg set wg0 peer {result.public_key} remove"
        process = await asyncio.create_subprocess_shell(command)
        await process.communicate()  # Ensure command execution completes
        
        await self.db.delete(result)
        await self.log_action(current_user.username, "Removed peer", result.peer_name)
        return {"message": f"Peer {result.peer_name} removed successfully"}
