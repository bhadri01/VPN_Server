from datetime import datetime
from sqlalchemy import TIMESTAMP, Column, ForeignKey, Insert, Integer, String,event, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import Base, get_session,master_db_engine
from app.utils.password_utils import get_password_hash
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"
    username = Column(String, unique=True, index=True)
    role_id = Column(String,ForeignKey("roles.id"),nullable=False)
    password = Column(String,nullable=False)
    

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    admin_username = Column(String, index=True)
    action = Column(String)
    target = Column(String)
    timestamp = Column(TIMESTAMP, default=datetime.utcnow)
    

# def create_default_user(target, connection, **kwargs):
#     hashed_password = get_password_hash("admin@123")  # Default password
#     connection.execute(
#         User.__table__.insert().values(
#             username="admin",
#             role="admin",
#             password=hashed_password
#         )
#     )

# # Listen for table creation event
# event.listen(User.__table__, "after_create", create_default_user)


async def create_default_user():
    async for session in get_session():
        from app.api.roles.models import Role, RoleEnum
        from app.api.peers.models import WireGuardIPPool

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

        admin_role = await session.execute(select(Role.id).where(Role.role == RoleEnum.admin.value))
        admin_role_id = admin_role.scalar_one_or_none()

        if admin_role_id:
            user_check = await session.execute(select(User.username).where(User.username == "admin"))
            if not user_check.scalar_one_or_none():
                hashed_password = get_password_hash("admin@123")
                await session.execute(
                    insert(User).values(
                        username="admin",
                        role_id=admin_role_id,
                        password=hashed_password
                    )
                )
                await session.commit()
        break