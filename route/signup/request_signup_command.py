# route/signup/request_signup_command.py

from pydantic import BaseModel, Field
from domain.user import UserCreate, UserUpdate

class SignupCommand(BaseModel):
  request: UserCreate = Field(..., description="회원가입 사용자 정보")

class ModifyUserCommand(BaseModel):
  user_id: str = Field(..., description="수정할 사용자 ID")
  request: UserUpdate = Field(..., description="수정할 사용자 정보")