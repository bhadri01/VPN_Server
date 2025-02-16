

from datetime import timedelta
import re
from unittest import result
from fastapi import HTTPException
from sqlalchemy import select
from app.api.peers.models import WireGuardPeer
from app.api.users.models import AuditLog, User
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.wg_server.models import WGServerConfig
from app.core.database import get_session
from app.utils.password_utils import get_password_hash, verify_password
from app.utils.security import TOKEN_EXPIRE_MINUTES, create_access_token


class user_service:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    async def log_action(admin_username, action, target, db: AsyncSession):
        log_entry = AuditLog(admin_username=admin_username,
                             action=action, target=target)
        db.add(log_entry)
        await db.commit()

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
    async def authenticate_user(username: str, db: AsyncSession):
        result = await db.execute(select(User).filter_by(username=username))
        return result.scalar_one_or_none()
    

    async def admin_check(self,current_user):
        await self.is_admin(current_user)
        return {"message": "User is an admin"}


    async def user_login(self, data):
        result = await self.db.execute(
            select(User).where(User.username == data.username)
        )
        user = result.scalars().first()

        if not user or not verify_password(data.password, user.password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        access_token = create_access_token(
            data={"username": user.username, "role": user.role_id}, expires_delta=timedelta(minutes=TOKEN_EXPIRE_MINUTES))
        return {"access_token": access_token, "token_type": "bearer", "user_id": user.id}

    async def create_user(self, data, current_user: User):
        """ Ensure only admins can create users without nested transactions """

        await self.is_admin(current_user)  # ✅ Properly await the function

        #Check if user already exists (use `await self.db.execute()`)
        result = await self.db.execute(select(User).where(User.username == data.username))
        existing_user = result.scalars().first()

        if existing_user:
            raise HTTPException(status_code=400, detail="User already exists")
        # Hash the password (ensure it's sync-safe)
        hashed_password = get_password_hash(data.password)
        # Create a new user
        new_user = User(username=data.username,
                        password=hashed_password, role_id=data.role_id)
        self.db.add(new_user)
        
        # Logging action AFTER commit to prevent nested transactions
        await self.log_action(current_user.username, "Created user", data.username, self.db)
        return {"message": f"User {data.username} created successfully"}
    
    async def get_all_users(self, current_user):
        await self.is_admin(current_user)
        query = await self.db.execute(select(User))
        users = query.scalars().all()
        if not users:
            raise HTTPException(status_code=404, detail="No users found")
        
        for user in users:
            peer_count_query = await self.db.execute(select(WireGuardPeer).where(WireGuardPeer.user_id == user.id))
            peer_count = len(peer_count_query.scalars().all())
            user.peer_count = peer_count
        
        return users
        
    async def get_user(self, current_user):
        print("Username",current_user.username)
        query = await self.db.execute(select(User).where(User.username == current_user.username))
        result = query.scalars().first()
        return result
        
    async def get_user_by_id(self, user_id, current_user):
        await self.is_admin(current_user)
        query = await self.db.execute(select(User).where(User.id == user_id))
        result = query.scalars().first()
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
        # Calculate peer count for the user
        peer_count_query = await self.db.execute(select(WireGuardPeer).where(WireGuardPeer.user_id == result.id))
        peer_count = len(peer_count_query.scalars().all())
        result.peer_count = peer_count
        return result

    async def delete_user(self,user_id, current_user):
        await self.is_admin(current_user)
        query = await self.db.execute(select(User).where(User.id == user_id))
        result = query.scalars().first()

        if not result:
            raise HTTPException(status_code=404, detail="User not found")
        await self.db.delete(result)
        await self.log_action(current_user.username, "Deleted user", result.username, self.db)
        return {"message": f"User {result.username} deleted successfully"}
    
    async def edit_user(self,user_id, data, current_user):
        await self.is_admin(current_user)
        query = await self.db.execute(select(User).where(User.id == user_id))
        result = query.scalars().first()

        if not result:
            raise HTTPException(status_code=404, detail="User not found")
        
        if data.username:
            result.username = data.username
        if data.role_id:
            result.role_id = data.role_id
        if data.password:
            result.password = get_password_hash(data.password)

        await self.db.commit()
        await self.log_action(current_user.username, "Edited user", result.username, self.db)
        return {"message": f"User {result.username} edited successfully"}