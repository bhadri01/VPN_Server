from fastapi import APIRouter, Depends

from app.api.roles.schemas import AddRole, UpdateRole
from app.api.roles.services import role_services
from app.core.database import get_session

from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.httpbearer import get_current_user

router = APIRouter()  


@router.get("")
async def read_roles(db: AsyncSession = Depends(get_session),current_user = Depends(get_current_user)):
    result = await role_services(db).get_roles(current_user)
    return result

@router.post("")
async def create_role(data: AddRole, db: AsyncSession = Depends(get_session),current_user = Depends(get_current_user)):
    result = await role_services(db).add_role(data, current_user)
    return result

@router.put("/{role_id}")
async def update_role(role_id: str, data: UpdateRole, db: AsyncSession = Depends(get_session),current_user = Depends(get_current_user)):
    result = await role_services(db).update_role(role_id, data, current_user)
    return result

@router.delete("/{role_id}")
async def delete_role(role_id: str, db: AsyncSession = Depends(get_session),current_user = Depends(get_current_user)):
    result = await role_services(db).delete_role(role_id, current_user)
    return result
    
     