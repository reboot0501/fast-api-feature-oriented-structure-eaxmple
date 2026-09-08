# route/signup/request_signup_fetch.py

from pydantic import BaseModel, Field

class FindSignedUserFetch(BaseModel):
  user_id: str = Field(..., min_length=1, description="조회할 사용자 ID")

class FindSignupDeptsFetch(BaseModel):
  dept_name: str | None = Field(default=None, description="검색할 부서명 (선택)")
