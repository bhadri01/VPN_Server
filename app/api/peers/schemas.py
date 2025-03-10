from http import server
from typing import Optional
from pydantic import BaseModel

class AddPeerRequest(BaseModel):
    ip: Optional[str] = None  # ✅ ip is now optional
    peer_name: str
    
    
class DeletePeer(BaseModel):
    peer_id : str
    
    
class EditPeer(BaseModel):
    ip : Optional[str] = None
    peer_name : Optional[str] = None

class TransferData(BaseModel):
    rx : int
    tx : int