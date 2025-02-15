from datetime import datetime
from sqlalchemy import TIMESTAMP, Column, Integer, String,event, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import Base,master_db_engine
from app.utils.password_utils import get_password_hash
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"
    username = Column(String, unique=True, index=True)
    role = Column(String, default="user")
    password = Column(String,nullable=False)
    

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    admin_username = Column(String, index=True)
    action = Column(String)
    target = Column(String)
    timestamp = Column(TIMESTAMP, default=datetime.utcnow)
    

def create_default_user(target, connection, **kwargs):
    hashed_password = get_password_hash("admin@123")  # Default password
    connection.execute(
        User.__table__.insert().values(
            username="admin",
            role="admin",
            password=hashed_password
        )
    )

# Listen for table creation event
event.listen(User.__table__, "after_create", create_default_user)