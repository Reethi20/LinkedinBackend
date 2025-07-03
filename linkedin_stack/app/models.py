from pydantic import BaseModel
from typing import Optional

class AutoGenerateRequest(BaseModel):
    length: str
    additional_instructions: Optional[str] = None

class ManualGenerateRequest(BaseModel):
    topic: str
    length: str
    additional_instructions: Optional[str] = None

class GeneratedPost(BaseModel):
    content: str

class JobResponse(BaseModel):
    task_id: str

class JobResult(BaseModel):
    post_id: Optional[str] = None
    content: Optional[str] = None
    error: Optional[str] = None

class JobStatus(BaseModel):
    task_id: str
    status: str  # e.g., "pending", "completed", "failed"
    result: Optional[JobResult] = None

class TokenData(BaseModel):
    id: str


class PostBase(BaseModel):
    content: str

class PostCreate(PostBase):
    pass

class PostUpdate(PostBase):
    pass

class Post(PostBase):
    id: str
    created_at: str
    updated_at: str

    class Config:
        orm_mode = True
