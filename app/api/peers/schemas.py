from http import server
from typing import Optional
from pydantic import BaseModel

class AddPeerRequest(BaseModel):
    server_id: str
    ip: Optional[str] = None  # ✅ ip is now optional
    peer_name: str
    
    
class DeletePeer(BaseModel):
    peer_id : str
    
    
class EditPeer(BaseModel):
    ip : str
    peer_name : str
