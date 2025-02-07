

from fastapi import APIRouter, Depends

from app.api.peers.schemas import AddPeerRequest, DeletePeer, EditPeer
from .services import peer_service
from app.core.database import get_session
from app.utils.httpbearer import get_current_user

from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.get("")
async def get_peers(db: AsyncSession = Depends(get_session)):
    result = await peer_service(db).get_all_peers()
    return result

@router.get("/{peer_id}")
async def get_single_peer(peer_id : str,db:AsyncSession=Depends(get_session)):
    result = await peer_service(db).get_peer(peer_id)
    return result

@router.post("/{user_id}")
async def add_peers(user_id : str ,data: AddPeerRequest, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    service = peer_service(db)
    result = await service.add_peer(user_id,data, current_user)
    return result

@router.delete("/{peer_id}")
async def add_peers(peer_id: str, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    result = await peer_service(db).remove_peer(peer_id,current_user)
    return result


@router.put("/{peer_id}")
async def edit_peers(peer_id : str , data : EditPeer , current_user=Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    result = await peer_service(db).update_peer(peer_id,data,current_user)
    return result

@router.get("/generate-peer-config/{peer_id}")
async def generate_peer_config(peer_id : str, db: AsyncSession = Depends(get_session)):
    result = await peer_service(db).generate_peer_config(peer_id)
    return result

