from pydantic import BaseModel


class AddPeerRequest(BaseModel):
    user_id : str
    peer_name: str
    
class DeletePeer(BaseModel):
    peer_id : str