

import os
import subprocess
from typing import Tuple

from sqlalchemy import select
from app.api.wg_server.models import WGServerConfig
from app.utils.password_utils import get_password_hash
from fastapi import HTTPException


class wg_server:
    def __init__(self, db):
        self.db = db

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
                f"Error generating WireGuard keys: {e.stderr.decode().strip()}"
            )

    @staticmethod
    def add_keys_to_wg0_conf(private_key: str, data) -> None:
        """Adds the generated keys to the wg0.conf file"""
        wg0_conf_path = f"/etc/wireguard/{data.server_name}.conf"
        try:
            with open(wg0_conf_path, "a") as wg0_conf:
                wg0_conf.write(
                    f"\n[Interface]\nAddress = {data.address}\nSaveConfig = True\n"
                    f"PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth+ -j MASQUERADE\n"
                    f"PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth+ -j MASQUERADE\n"
                    f"ListenPort = {data.listen_port}\nPrivateKey = {private_key}\n"
                )
        except IOError as e:
            raise RuntimeError(
                f"Error writing to wg0.conf: {str(e)}"
                    )  
        
    async def get_servers(self):
        query = await self.db.execute(select(WGServerConfig))
        servers = query.scalars().all()
        return servers

    async def get_server(self, server_id):
        server = await self.db.get(WGServerConfig, server_id)
        if server is None:
            raise HTTPException(status_code=404, detail="Server not found")
        return server
        
    async def create_server(self, data):
        private_key, public_key = self.generate_wg_key_pair()
        self.add_keys_to_wg0_conf(private_key,data)
        server = WGServerConfig(
            **data.model_dump(), public_key=public_key, private_key=private_key)
        self.db.add(server)
        await self.db.commit()
        return {"message": "Server Created Successfully"}
    
    async def delete_server(self, server_id):
        server = await self.db.get(WGServerConfig, server_id)
        if server is None:
            raise HTTPException(status_code=404, detail="Server not found")
        

        # Attempt to delete the server configuration file
        wg0_conf_path = f"/etc/wireguard/{server.server_name}.conf"
        try:
            os.remove(wg0_conf_path)
        except OSError as e:
            # Log the error but do not raise an exception
            print(f"Error deleting server file: {str(e)}")
        # Delete the server entry from the database
        await self.db.delete(server)
        await self.db.commit()

        return {"message": "Server Deleted Successfully"}
