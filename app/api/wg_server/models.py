from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, String
from app.core.database import Base
from sqlalchemy.orm import relationship

class WGServerConfig(Base):
    __tablename__ = 'wg_server_config'

    entry = Column(Integer, default=1, nullable=False, unique=True)
    server_name = Column(String(100), unique=True, nullable=False)
    address = Column(String(100), unique=True, nullable=False)
    listen_port = Column(Integer, unique=True, nullable=False)
    private_key = Column(String(100), unique=True, nullable=False)
    public_key = Column(String(100), unique=True, nullable=False)

    peers = relationship("WireGuardPeer", back_populates="wg_server")

    __table_args__ = (
        CheckConstraint("entry = 1", name="single_row_check"),
    )