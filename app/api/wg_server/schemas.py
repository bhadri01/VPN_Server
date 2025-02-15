from typing import Optional


from app.utils.password_utils import verify_password
from pydantic import BaseModel
from datetime import datetime

class WGServerSchema(BaseModel):
    
    server_name : str
    address : str
    listen_port : int


    class Config:
        from_attributes = True
        from_attributes = True

class WGServerResponseSchema(BaseModel):
    
    id : str
    created_at : datetime
    updated_at : datetime
    created_by : Optional[str]
    updated_by : Optional[str]
    server_name : str
    address : str
    listen_port : int
    private_key : str
    # public_key : str

    class Config:
        from_attributes = True
    
    def model_validate(cls, obj):
        obj.private_key = verify_password(obj.private_key)
        obj.public_key = verify_password(obj.public_key)
        return super().from_orm(obj)