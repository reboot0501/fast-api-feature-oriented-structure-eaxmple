# route/organiztion/request_organization_fetch.py

from pydantic import BaseModel, Field

class FindUsersFetch(BaseModel):
  user_name: str | None = Field(default=None, description="검색할 사용자 이름")
  dept_id: str | None = Field(default=None, description="소속 부서 ID")
  page: int = Field(default=1, ge=1, description="페이지 번호 (1부터 시작)")
  size: int = Field(default=10, ge=1, le=100, description="페이지당 개수 (기본 10개, 최대 100개)")
  order: str = Field(default="desc", pattern="^(asc|desc)$", description="정렬 방향 (asc 또는 desc)")

class FindDeptsFetch(BaseModel):
  dept_name: str | None = Field(default=None, description="검색할 부서명")
  page: int = Field(default=1, ge=1, description="페이지 번호 (1부터 시작)")
  size: int = Field(default=10, ge=1, le=100, description="페이지당 개수 (기본 10개, 최대 100개)")
  order: str = Field(default="desc", pattern="^(asc|desc)$", description="정렬 방향 (asc 또는 desc)")