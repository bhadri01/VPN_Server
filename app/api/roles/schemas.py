from typing import Optional
from pydantic import BaseModel

class AddRole(BaseModel):
    role: str

class UpdateRole(BaseModel):    
    role: Optional[str] = None

