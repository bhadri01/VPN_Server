from math import log
import re
from fastapi import HTTPException
from httpx import delete
from sqlalchemy import select

from app.api.roles.models import Role
from app.api.users.models import AuditLog, User
from app.core.database import get_session
from .schemas import AddRole, UpdateRole
from sqlalchemy.ext.asyncio import AsyncSession

class role_services:
    def __init__(self, db):
        self.db = db

    @staticmethod
    async def is_admin(user: User):
        if not hasattr(user, "role_id"):  # ✅ Ensure role_id exists in User model
            raise HTTPException(status_code=500, detail="User model does not have role_id")

        async for session in get_session():
            from app.api.roles.models import Role, RoleEnum
            
            # ✅ Fetch the Role ID for "admin"
            admin_role = await session.execute(select(Role.id).where(Role.role == RoleEnum.admin.value))
            admin_role_id = admin_role.scalar_one_or_none()

            if not admin_role_id:
                raise HTTPException(status_code=500, detail="Admin role not found in database")

            # ✅ Compare user's role ID with the admin role ID
            if user.role_id != admin_role_id:
                raise HTTPException(status_code=403, detail="Admin access required")

            break  # ✅ Exit after checking

    @staticmethod
    async def log_action(admin_username, action, target, db: AsyncSession):
        log_entry = AuditLog(admin_username=admin_username,
                             action=action, target=target)
        db.add(log_entry)
        await db.commit()

    async def get_roles(self,current_user):
        await self.is_admin(current_user)
        query = await self.db.execute(select(Role))
        result = query.scalars().all()
        return result
    
    async def add_role(self, data: AddRole,current_user):

        await self.is_admin(current_user)
        role = Role(**data.model_dump())
        self.db.add(role)
        await self.db.commit()
        await self.log_action(current_user.username, "Added Role", role.role, self.db)
        return {"message":"Role added successfully"}

    async def update_role(self, role_id, data,current_user):
        await self.is_admin(current_user)
        role = await self.db.execute(select(Role).where(Role.id == role_id))
        role = role.scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        
        for key, value in data.model_dump().items():
            setattr(role, key, value)
        await self.db.commit()
        await self.log_action(current_user.username, "Updated Role", role.role, self.db)
        return {"message":"Role updated successfully"}
    
    async def delete_role(self, role_id,current_user):
        await self.is_admin(current_user)
        role = await self.db.execute(select(Role).where(Role.id == role_id))
        role = role.scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        await self.db.delete(role)
        await self.db.commit()
        await self.log_action(current_user.username, "Deleted Role", role.role, self.db)
        return {"message":"Role deleted successfully"}