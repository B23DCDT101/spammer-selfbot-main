from pydantic import BaseModel
from typing import Optional


class TodoCreate(BaseModel):
    title: str
    description: Optional[str] = None
    user_id: str  # Discord user ID


class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    done: Optional[bool] = None


class TodoOut(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    done: bool
    user_id: str
