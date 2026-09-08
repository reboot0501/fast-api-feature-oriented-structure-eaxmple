# feature/organization/organization_fetch.py

from domain.dept import Dept, DeptResponse, DeptLogic
from domain.user import User, UserResponse, UserLogic
from shared.models import OffsetElementList

class OrganizationFetch:
  def __init__(self, user_logic: UserLogic, dept_logic: DeptLogic):
    self.user_logic = user_logic
    self.dept_logic = dept_logic

  def find_users(
    self, 
    user_name: str | None = None, 
    dept_id: str | None = None, 
    page: int = 1, 
    size: int = 10, 
    order: str = "desc"
  ) -> OffsetElementList[UserResponse]:
    pagination = self.user_logic.retrieve_users_by_name_like_and_dept_id_paginated(
      user_name,
      dept_id,
      page,
      size,
      order,
    )
    extracted_users = pagination.items

    # 3) 중복 없는 dept_id 집합 추출 : { ... } 문법으로 작성하면 중복된 dept_id가 자동으로 제거된 set[str]이 생성됩니다.
    dept_ids = {user.dept_id for user in extracted_users if user.dept_id}

    # 4) IN (:dept_ids) 쿼리로 부서들을 단 1번의 쿼리로 일괄 조회 (배치 조회)
    depts = self.dept_logic.retrieve_depts_by_ids(list(dept_ids))

    # 5) O(1) 조회를 위한 ID -> 부서명 딕셔너리(Map) 구성
    dept_map = {str(dept.id): dept.name for dept in depts}

    # 6) 유저 목록을 돌면서 부서명(dept_name) 매핑 및 UserResponse 변환
    user_responses = []
    for user in extracted_users:
      user.dept_name = dept_map.get(user.dept_id)
      user_responses.append(UserResponse.model_validate(user))

    # 7) 최종 페이징 객체 생성 및 반환
    return OffsetElementList.of(
      user_responses,
      pagination.total_count,
      pagination.page,
      pagination.size,
    )

  def find_depts(
    self, 
    dept_name: str | None = None, 
    page: int = 1, 
    size: int = 10, 
    order: str = "desc"
  ) -> OffsetElementList[DeptResponse]:
    pagination = self.dept_logic.retrieve_depts_by_name_like_paginated(
      dept_name,
      page,
      size,
      order,
    )
    extracted_depts = pagination.items
    
    # 3) 부서 목록을 돌면서 DeptResponse 변환
    dept_responses = [DeptResponse.model_validate(d) for d in extracted_depts]
    
    # 4) 최종 페이징 객체 생성 및 반환
    return OffsetElementList.of(
      dept_responses,
      pagination.total_count,
      pagination.page,
      pagination.size,
    )

