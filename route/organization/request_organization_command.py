# route/organiztion/request_organization_command.py

from shared.models import IdNameValues
from pydantic import BaseModel, Field
from domain.dept import DeptCreate

class RegisterDeptsCommand(BaseModel):
  depts: list[DeptCreate] = Field(..., min_length=1, description="등록할 부서 목록")

class ModifyDeptsCommand(BaseModel):
  depts: list[IdNameValues] = Field(..., min_length=1, description="수정할 부서 목록")

class RemoveDeptsCommand(BaseModel):
  depts: list[str] = Field(..., min_length=1, description="삭제할 부서 ID 목록")

class ChangeUsersDeptCommand(BaseModel):
  users: list[IdNameValues] = Field(..., min_length=1, description="사용자별 부서 변경 목록")
