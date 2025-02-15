

from datetime import timedelta
from unittest import result
from fastapi import HTTPException
from sqlalchemy import select
from app.api.users.models import AuditLog, User
from sqlalchemy.ext.asyncio import AsyncSession

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
    def is_admin(user: User):
        if user.role != "admin":
            raise HTTPException(
                status_code=403, detail="Admin access required")
            
    @staticmethod
    async def authenticate_user(username: str, db: AsyncSession):
        result = await db.execute(select(User).filter_by(username=username))
        return result.scalar_one_or_none()

    async def user_login(self, data):
        result = await self.db.execute(
            select(User).where(User.username == data.username)
        )
        user = result.scalars().first()

        if not user or not verify_password(data.password, user.password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        access_token = create_access_token(
            data={"username": user.username, "role": user.role}, expires_delta=timedelta(minutes=TOKEN_EXPIRE_MINUTES))
        return {"access_token": access_token, "token_type": "bearer"}

    async def create_user(self, data, current_user: User):
        """ Ensure only admins can create users without nested transactions """

        self.is_admin(current_user)  # Ensure only admins can create users
        # Check if user already exists (use `await self.db.execute()`)
        result = await self.db.execute(select(User).where(User.username == data.username))
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(status_code=400, detail="User already exists")
        # Hash the password (ensure it's sync-safe)
        hashed_password = get_password_hash(data.password)
        # Create a new user
        new_user = User(username=data.username,
                        password=hashed_password, role=data.role)
        self.db.add(new_user)
        
        # Logging action AFTER commit to prevent nested transactions
        await self.log_action(current_user.username, "Created user", data.username, self.db)
        return {"message": f"User {data.username} created successfully"}
    
    async def get_all_users(self):
        query = await self.db.execute(select(User))
        return query.scalars().all()

    async def get_user_peers_count(self, username: str):
        user = await self.authenticate_user(username, self.db)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Assuming there is a relationship defined in the User model to get peers
        peers_count = len(user.peers)  # Replace 'peers' with the actual relationship attribute
        return {"username": username, "peers_count": peers_count}

    async def get_user(self, current_user):
        query = await self.db.execute(select(User).where(User.username == current_user.username))
        result = query.scalars().first()
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
        return result