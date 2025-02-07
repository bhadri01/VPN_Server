from unittest import result
from fastapi import APIRouter, Depends

from app.api.users.models import User
from app.api.users.schemas import CreateUserRequest, UserLoginSchema
from app.api.users.services import user_service
from app.core.database import get_session
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.httpbearer import get_current_user
from app.utils.security import authenticate_user

router = APIRouter()


@router.post("/login")
async def user_login(data: UserLoginSchema, db: AsyncSession = Depends(get_session)):
    result = await user_service(db).user_login(data)
    return result


@router.get("")
async def get_users(db: AsyncSession = Depends(get_session),
                    current_user=Depends(get_current_user)):
    result = await user_service(db).get_all_users()
    return result


@router.post("")
async def create_user(
    data: CreateUserRequest,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user)
):
    result = await user_service(db).create_user(data, current_user)
    return result

@router.get("/me")
async def get_user(db : AsyncSession = Depends(get_session),current_user = Depends(get_current_user)):
    result = await user_service(db).get_user(current_user)
    return result