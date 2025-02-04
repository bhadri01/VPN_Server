from sqlalchemy import Column, ForeignKey, Integer, String
from app.core.database import Base


class WireGuardPeer(Base):
    __tablename__ = "wireguard_peers"
    user_id = Column(Integer, ForeignKey("users.id"))
    peer_name = Column(String, index=True)
    public_key = Column(String, unique=True, index=True)
    assigned_ip = Column(String, unique=True, index=True)