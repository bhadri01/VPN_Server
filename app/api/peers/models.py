from sqlalchemy import Boolean, Column, ForeignKey, String
from app.core.database import Base


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
