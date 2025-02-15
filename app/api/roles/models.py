from sqlalchemy import Column,String
from app.core.database import Base
from enum import Enum

class RoleEnum(Enum):
    admin = "admin"
    user = "user"
    maintainer = "maintainer"


class Role(Base):
    __tablename__ = "role"

    role = Column(String, unique=True)


    
    




