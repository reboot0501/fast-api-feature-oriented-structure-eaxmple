# feature/organization/organization_flow.py

from copy import copy

from app.config.transaction import transactional
from shared.models.exception import (
  DeptNotFoundException,
  UpdateValueException,
  UserNotFoundException,
  DeptHasUsersException,
)
from shared.models import IdNameValues
from shared.utils import get_modified_name_values
from domain.dept import DeptResponse
from domain.dept import DeptCreate
from domain.dept import DeptLogic
from domain.user import UserLogic
from domain.user import User


class OrganizationFlow:
  def __init__(self, user_logic: UserLogic, dept_logic: DeptLogic):
    self.user_logic = user_logic
    self.dept_logic = dept_logic

  @transactional
  def register_dept(self, dept_create: DeptCreate) -> DeptResponse:
    """
    단일 부서 등록
    """
    return self.dept_logic.register_dept(dept_create)

  @transactional
  def register_depts(self, dept_creates: list[DeptCreate]) -> list[DeptResponse]:
    """
    부서 여러개 등록
    """
    return [self.register_dept(dept_create) for dept_create in dept_creates]
  
  @transactional
  def modify_dept(self, dept_update: IdNameValues) -> DeptResponse:
    """
    단일 부서 수정 (IdNameValues 기반)
    """
    dept = self.dept_logic.retrieve_dept_by_id(dept_update.id)
    if not dept:
      raise DeptNotFoundException(dept_update.id)

    # 요청값을 복사본에 먼저 반영해 기존 Entity와 실제 변경 내용을 비교한다.
    candidate_dept = copy(dept)
    for key, value in dept_update.to_dict().items():
      setattr(candidate_dept, key, value)

    modified_values = get_modified_name_values(dept, candidate_dept)
    if not modified_values:
      # 변경된 속성이 없으면 불필요한 Domain/Repository update를 수행하지 않는다.
      return DeptResponse.model_validate(dept)

    update_data = {
      name_value.name: name_value.value
      for name_value in modified_values
    }
    updated_dept = self.dept_logic.modify_dept(dept, update_data)
    return DeptResponse.model_validate(updated_dept)

  @transactional
  def modify_depts(self, dept_updates: list[IdNameValues]) -> list[DeptResponse]:
    """
    부서 여러개 일괄 수정 (하나라도 실패 시 전체 롤백)
    """
    return [self.modify_dept(dept_update) for dept_update in dept_updates]


  @transactional
  def change_user_dept(self, user_change: IdNameValues) -> bool:
    """
    사용자 부서 변경
    """
    update_data = user_change.to_dict()
    if set(update_data) != {"dept_id"}:
      raise UpdateValueException()

    user = self.user_logic.retrieve_user_by_id(user_change.id)
    if not user:
      raise UserNotFoundException(user_change.id)

    new_dept_id = update_data["dept_id"]
    new_dept = self.dept_logic.retrieve_dept_by_id(new_dept_id)
    if not new_dept:
      raise DeptNotFoundException(new_dept_id)

    return self.user_logic.change_user_dept(user, new_dept_id)

  @transactional
  def change_users_dept(self, user_changes: list[IdNameValues]) -> list[bool]:
    """
    사용자 여러명 부서 변경
    """
    return [self.change_user_dept(user_change) for user_change in user_changes]

  @transactional
  def remove_dept(self, dept_id: str) -> bool:
    """
    부서 삭제
    """
    extracted_users: list[User] = self.user_logic.retrieve_users_by_dept_id(dept_id)  # 부서에 소속된 사용자가 있는지 확인 (없으면 예외 발생)
    if extracted_users:
      raise DeptHasUsersException(dept_id)
    return self.dept_logic.remove_dept(dept_id)

  @transactional
  def remove_depts(self, dept_ids: list[str]) -> list[bool]:
    """
    부서 여러개 삭제
    """
    return [self.remove_dept(dept_id) for dept_id in dept_ids]
  
  