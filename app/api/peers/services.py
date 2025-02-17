import asyncio
from ipaddress import IPv4Network
import os
import re
import stat
import subprocess
from typing import Tuple
import aiofiles
from fastapi import HTTPException
from httpx import get
from sqlalchemy import  select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.peers.models import WireGuardIPPool, WireGuardPeer
from app.api.users.models import AuditLog
from app.api.wg_server.models import WGServerConfig
from app.utils.ip_pool import get_next_available_ip
from app.core.config import settings



class peer_service:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    async def log_action(admin_username, action, target, db: AsyncSession):
        log_entry = AuditLog(admin_username=admin_username,
                             action=action, target=target)
        db.add(log_entry)
        await db.commit()


    @staticmethod
    def generate_wg_key_pair() -> Tuple[str, str]:
        """Generates a WireGuard key pair (private key & public key)"""

        try:
            # Generate private key
            private_key = subprocess.check_output(
                "wg genkey", shell=True, stderr=subprocess.PIPE).decode().strip()

            # Generate public key from private key
            public_key = subprocess.check_output(
                f"echo {private_key} | wg pubkey", shell=True, stderr=subprocess.PIPE).decode().strip()

            return private_key, public_key

        except subprocess.CalledProcessError as e:
            # Handle subprocess errors (e.g., if WireGuard tools are missing)
            raise RuntimeError(
                f"Error generating WireGuard keys: {e.stderr.decode().strip()}")
        
    async def get_all_peers(self, user_id):
        query = await self.db.execute(select(WireGuardPeer).where(WireGuardPeer.user_id == user_id))
        result = query.scalars().all()
        return result

    async def get_peer(self, peer_id):
        """Fetch a specific peer by ID."""
        query = await self.db.execute(select(WireGuardPeer).where(WireGuardPeer.id == peer_id))
        peer = query.scalars().first()
        if not peer:
            raise HTTPException(status_code=404, detail="Peer not found")
        return peer

    async def add_peer(self, user_id, data, current_user):
        assigned_ip = await get_next_available_ip(self.db,data.ip)
        private_key, public_key = self.generate_wg_key_pair()


        server = await self.db.execute(select(WGServerConfig))
        server = server.scalars().first()

        if server is None:
            raise HTTPException(status_code=404, detail="WireGuard server config not found")
        
        print(server.interface_name)

        new_peer = WireGuardPeer(
            user_id=user_id,
            peer_name=data.peer_name,
            public_key=public_key,
            private_key=private_key,
            assigned_ip=assigned_ip,
            server_id=server.id
        )


        if server is None:
            raise HTTPException(
                status_code=404, detail="WireGuard server config not found")

        # Log action in the database
        command = f"wg set {server.interface_name} peer {public_key} allowed-ips {assigned_ip}/32"
        process = await asyncio.create_subprocess_shell(command)
        await process.communicate()  # Ensure command execution completes

        command = f"wg-quick save {server.interface_name}"
        process = await asyncio.create_subprocess_shell(command)
        await process.communicate()

        self.db.add(new_peer)
        await self.db.commit()  # Ensure commit is awaited
        await self.log_action(current_user.username, "Added peer", data.peer_name, self.db)

        return {"message": "Peer Created Successfully"}

    async def remove_peer(self, peer_id, current_user):
        peer = await self.db.execute(select(WireGuardPeer).where(WireGuardPeer.id == peer_id).options(joinedload(WireGuardPeer.wg_server)))
        result = peer.scalars().first()

        if result == None:
            raise HTTPException(
                detail="Peer Not Found",
                status_code=404
            )

        command = f"wg set {result.wg_server.interface_name} peer {result.public_key} remove"
        process = await asyncio.create_subprocess_shell(command)
        await process.communicate()  # Ensure command execution completes

        command = f"wg-quick save {result.wg_server.interface_name}"
        process = await asyncio.create_subprocess_shell(command)
        await process.communicate()  # Ensure command execution completes

        # Mark the assigned IP as available in the WireGuardIPPool table
        ip_entry = await self.db.execute(
            select(WireGuardIPPool).where(WireGuardIPPool.ip_address == result.assigned_ip)
        )
        ip_result = ip_entry.scalars().first()

        if ip_result:
            ip_result.is_assigned = False
            self.db.add(ip_result)  # Mark as available

        await self.db.delete(result)
        await self.log_action(current_user.username, "Removed peer", result.peer_name, self.db)
        return {"message": f"Peer {result.peer_name} removed successfully"}

    async def update_peer(self, peer_id, data, current_user):
        private_key, public_key = self.generate_wg_key_pair()
        peer = await self.db.execute(select(WireGuardPeer).where(WireGuardPeer.id == peer_id).options(joinedload(WireGuardPeer.wg_server)))
        result = peer.scalars().first()
        if result is None:
            raise HTTPException(
                detail="Peer Not Found",
                status_code=404
            )
        if data.peer_name:
            result.peer_name = data.peer_name
        if data.ip:
            result.assigned_ip = data.ip

        command = f"wg set {result.wg_server.interface_name} peer {result.public_key} remove"
        process = await asyncio.create_subprocess_shell(command)
        await process.communicate()  # Ensure command execution completes

        # Log action in the database
        command = f"wg set {result.wg_server.interface_name} peer {public_key} allowed-ips {data.ip}/32"
        process = await asyncio.create_subprocess_shell(command)
        await process.communicate()  # Ensure command execution completes

        command = f"wg-quick save {result.wg_server.interface_name}"
        process = await asyncio.create_subprocess_shell(command)
        await process.communicate()  # Ensure command execution completes

                # Mark the assigned IP as available in the WireGuardIPPool table
        ip_entry = await self.db.execute(
            select(WireGuardIPPool).where(WireGuardIPPool.ip_address == result.assigned_ip)
        )
        ip_result = ip_entry.scalars().first()

        if ip_result:
            ip_result.is_assigned = False
            self.db.add(ip_result)  # Mark as available

        await self.db.commit()
        await self.log_action(current_user.username, "Updated peer", result.peer_name, self.db)

        return {"message": f"Peer {result.peer_name} updated successfully"}

    async def generate_peer_config(self, peer_id, current_user):
        query = await self.db.execute(select(WireGuardPeer).where(WireGuardPeer.id == peer_id).options(joinedload(WireGuardPeer.wg_server)))
        peer = query.scalars().first()
        if not peer:
            raise HTTPException(status_code=404, detail="Peer not found")
        
        peer_subnet = re.search(r"/(\d+)", peer.wg_server.server_ips).group(1)

        config = f"""
[Interface]
PrivateKey = {peer.private_key}
Address = {peer.assigned_ip}/{peer_subnet}

[Peer]
PublicKey = {peer.wg_server.public_key}
Endpoint = {settings.endpoint}
AllowedIPs = {settings.allowed_ips}
PersistentKeepalive = 30
"""
        # CONFIG_DIR = "/home"  # Define your config directory path
        # filename = f"{CONFIG_DIR}/{current_user.username}.conf"
        # os.makedirs(CONFIG_DIR, exist_ok=True)
        # async with aiofiles.open(filename, "w") as f:
        #     await f.write(config)

        return config
