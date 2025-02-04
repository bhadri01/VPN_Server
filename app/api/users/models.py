from datetime import datetime
from sqlalchemy import TIMESTAMP, Column, Integer, String
from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    username = Column(String, unique=True, index=True)
    

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    admin_username = Column(String, index=True)
    action = Column(String)
    target = Column(String)
    timestamp = Column(TIMESTAMP, default=datetime.utcnow)