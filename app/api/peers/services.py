import asyncio
from ipaddress import IPv4Network
import os
import stat
import subprocess
from typing import Tuple
import aiofiles
from fastapi import HTTPException
from httpx import get
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from websockets import serve
from sqlalchemy.orm import joinedload

from app.api.peers.models import WireGuardPeer
from app.api.users.models import AuditLog
from app.api.wg_server.models import WGServerConfig
from app.utils.ip_pool import get_next_available_ip




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

    async def get_all_peers(self):
        query = await self.db.execute(select(WireGuardPeer))
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
        assigned_ip = await get_next_available_ip(self.db)
        private_key, public_key = self.generate_wg_key_pair()

        new_peer = WireGuardPeer(
            user_id=user_id,
            peer_name=data.peer_name,
            public_key=public_key,
            private_key=private_key,
            assigned_ip=assigned_ip,
        )

        self.db.add(new_peer)
        await self.db.commit()  # Ensure commit is awaited

        # Fetch the WireGuard server config
        query = await self.db.execute(select(WGServerConfig))
        result = query.scalars().first()

        if result is None:
            raise HTTPException(
                status_code=404, detail="WireGuard server config not found")

        # Log action in the database
        command = f"wg set {result.interface_name} peer {public_key} allowed-ips {assigned_ip}/32"
        process = await asyncio.create_subprocess_shell(command)
        await process.communicate()  # Ensure command execution completes

        command = f"wg-quick save {result.interface_name}"
        process = await asyncio.create_subprocess_shell(command)
        await process.communicate()

        await self.log_action(current_user.username, "Added peer", data.peer_name, self.db)

        return {"message": "Peer Created Successfully"}

    async def remove_peer(self, peer_id, current_user):
        peer = await self.db.execute(select(WireGuardPeer).where(WireGuardPeer.id == peer_id))
        result = peer.scalars().first()

        if result == None:
            raise HTTPException(
                detail="Peer Not Found",
                status_code=404
            )

        command = f"wg set wg0 peer {result.public_key} remove"
        process = await asyncio.create_subprocess_shell(command)
        await process.communicate()  # Ensure command execution completes

        command = f"wg-quick save wg0"
        process = await asyncio.create_subprocess_shell(command)
        await process.communicate()  # Ensure command execution completes

        await self.db.delete(result)
        await self.log_action(current_user.username, "Removed peer", result.peer_name, self.db)
        return {"message": f"Peer {result.peer_name} removed successfully"}

    async def update_peer(self, peer_id, data, current_user):
        async with self.db.begin():
            peer = await self.db.execute(select(WireGuardPeer).where(WireGuardPeer.id == peer_id))
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

            await self.db.commit()
            await self.log_action(current_user.username, "Updated peer", result.peer_name, self.db)

        return {"message": f"Peer {result.peer_name} updated successfully"}

    async def generate_peer_config(self, peer_id, current_user):
        query = await self.db.execute(select(WireGuardPeer).where(WireGuardPeer.id == peer_id).options(joinedload(WireGuardPeer.wg_server)))
        result = query.scalars().first()
        if not result:
            raise HTTPException(status_code=404, detail="Peer not found")

        config = f"""
[Interface]
PrivateKey = {result.private_key}
Address = {result.assigned_ip}/24

[Peer]
PublicKey = {result.wg_server.public_key}
Endpoint = {os.getenv("ENDPOINT")}:{os.getenv("SERVER_PORT")}
AllowedIPs = {os.getenv("ALLOWED_IPS")}
PersistentKeepalive = 30
"""
        # CONFIG_DIR = "/home"  # Define your config directory path
        # filename = f"{CONFIG_DIR}/{current_user.username}.conf"
        # os.makedirs(CONFIG_DIR, exist_ok=True)
        # async with aiofiles.open(filename, "w") as f:
        #     await f.write(config)

        return config
