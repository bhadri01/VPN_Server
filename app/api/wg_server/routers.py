from ast import Assert
from typing import List
from fastapi import APIRouter, Depends

from app.api.wg_server.schemas import WGServerResponseSchema, WGServerSchema
from app.api.wg_server.services import wg_server
from app.core.database import get_session
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.httpbearer import get_current_user

router = APIRouter()

@router.get("/get")
async def get_servers(current_user = Depends(get_current_user), db: AsyncSession = Depends(get_session)) -> List[WGServerResponseSchema]:
    result = await wg_server(db).get_servers()
    return result

@router.get("/get/{server_id}")
async def get_server(server_id: str, current_user = Depends(get_current_user), db: AsyncSession = Depends(get_session)) -> WGServerResponseSchema:
    result = await wg_server(db).get_server(server_id)
    return result

@router.post("/create")
async def create_server(data: WGServerSchema, current_user = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    result = await wg_server(db).create_server(data)
    return result

@router.delete("/delete/{server_id}")
async def delete_server(server_id: str, current_user = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    result = await wg_server(db).delete_server(server_id)
    return result