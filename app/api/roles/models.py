from sqlalchemy import Column, String, event, insert, select
from app.core.database import Base, get_session
from enum import Enum
from app.utils.password_utils import get_password_hash


class RoleEnum(Enum):
    admin = "admin"
    user = "user"
    maintainer = "maintainer"


class Role(Base):
    __tablename__ = "role"
    role = Column(String, unique=True)  # Use primary key to ensure uniqueness
    


async def create_default_roles():
    async for session in get_session():  # ✅ Use async session
        from app.api.roles.models import Role
        # Check if roles exist
        result = await session.execute(select(Role.role).where(Role.role == RoleEnum.admin.value))
        if not result.scalar_one_or_none():  # If no roles exist, insert them
            await session.execute(
                insert(Role),
                [
                    {"role": RoleEnum.admin.value},
                    {"role": RoleEnum.user.value},
                    {"role": RoleEnum.maintainer.value},
                ],
            )
            await session.commit()  # ✅ Commit immediately
        break  # ✅ Exit after processing
