from sqlalchemy import Column, String
from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    username = Column(String, unique=True, index=True)
    
