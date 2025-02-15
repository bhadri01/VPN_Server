from asyncio import events
from operator import add
import subprocess
from typing import Tuple
from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, String
from app.core.database import Base
from sqlalchemy.orm import relationship

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
    address = Column(String(100), unique=True, nullable=False)
    listen_port = Column(Integer, unique=True, nullable=False)
    private_key = Column(String(100), unique=True, nullable=False)
    public_key = Column(String(100), unique=True, nullable=False)

    __table_args__ = (
        CheckConstraint("entry = 1", name="single_row_check"),
    )


# def create_default_server(target, connection, **kwargs):
#     connection.execute(
#             WGServerConfig.__table__.insert().values(
#                 server_name="wg-server-default",
#                 address="10.0.0.1",
#                 listen_port=51820,
#                 private_key=
#             )
#         )
