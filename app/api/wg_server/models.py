from asyncio import events
from operator import add
import os
import subprocess
from typing import Tuple
from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, String, event
from app.core.config import settings
from app.core.database import Base
from sqlalchemy.orm import relationship
from app.logs.logging import logger


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


class WGServerConfig(Base):
    __tablename__ = 'wg_server_config'

    entry = Column(Integer, default=1, nullable=False, unique=True)
    server_name = Column(String(100), unique=True, nullable=False)
    interface_name = Column(String(100), unique=True, nullable=False)
    address = Column(String(100), unique=True, nullable=False)
    listen_port = Column(Integer, unique=True, nullable=False)
    private_key = Column(String(100), unique=True, nullable=False)
    public_key = Column(String(100), unique=True, nullable=False)
    peers = relationship("WireGuardPeer", back_populates="wg_server")

    __table_args__ = (
        CheckConstraint("entry = 1", name="single_row_check"),
    )


private_key, public_key = generate_wg_key_pair()


def create_default_server(target, connection, **kwargs):
    # Extract required parameters from kwargs
    server_name = kwargs.get("server_name", f"{settings.servername}")
    interface_name = kwargs.get("interface_name", f"{settings.interface_name}")
    address = kwargs.get("address", f"{settings.address}")
    listen_port = kwargs.get("listen_port", 51820)
    private_key = kwargs.get("private_key", "")
    public_key = kwargs.get("public_key", "")
    wg0_conf_path = f"/etc/wireguard/wg1.conf"  # Make sure this path is correct

    if not private_key or not public_key:
        raise ValueError("Private key and public key must be provided.")

    # Append configuration to WireGuard config file
    with open(wg0_conf_path, "a") as wg0_conf:
        wg0_conf.write(
            f"\n[Interface]\nAddress = {address}\nSaveConfig = True\n"
            f"PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; "
            f"iptables -t nat -A POSTROUTING -o eth+ -j MASQUERADE\n"
            f"PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; "
            f"iptables -t nat -D POSTROUTING -o eth+ -j MASQUERADE\n"
            f"ListenPort = {listen_port}\nPrivateKey = {private_key}\n"
        )

    # Start the WireGuard server
    os.system(f"wg-quick up {server_name}")

    # Store configuration in the database
    connection.execute(
        WGServerConfig.__table__.insert().values(
            server_name=server_name,
            interface_name=interface_name,
            address=address,
            listen_port=listen_port,
            private_key=private_key,
            public_key=public_key
        )
    )

    logger.info(f"WireGuard server '{server_name}' created successfully!")


event.listen(
    WGServerConfig.__table__,
    "after_create",
    lambda target, connection, **kwargs: create_default_server(
        target, connection, private_key=private_key, public_key=public_key,address="10.11.0.1/16")
)
