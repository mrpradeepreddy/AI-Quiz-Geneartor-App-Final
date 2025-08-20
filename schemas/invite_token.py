from pydantic import BaseModel
from datetime import datetime

class InviteTokenBase(BaseModel):
    token: str
    assessment_id: int
    student_email: str
    used: bool
    expires_at: datetime

class InviteTokenResponse(BaseModel):
    title: str
    questions: list
    duration: int
    assessment_id: int
