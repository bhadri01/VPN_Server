

from fastapi import APIRouter, Depends

from app.api.peers.schemas import AddPeerRequest, DeletePeer
from .services import peer_service
from app.core.database import get_session
from app.utils.httpbearer import get_current_user

from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.get("")
async def get_peers(db: AsyncSession = Depends(get_session)):
    result = await peer_service(db).get_all_peers()
    return result

@router.post("")
async def add_peers(data: AddPeerRequest, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    service = peer_service(db)
    result = await service.add_peer(data, current_user)
    return result

@router.delete("")
async def add_peers(data: DeletePeer, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    result = await peer_service(db).remove_peer(data,current_user)
    return result
