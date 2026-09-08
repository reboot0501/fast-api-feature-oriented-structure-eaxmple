# feature/signup/signup_fetch.py

from domain.dept import DeptResponse
from shared.models.exception import UserNotFoundException
from shared.models.exception import DeptNotFoundException
from domain.user import UserResponse
from domain.dept import DeptLogic
from domain.user import UserLogic

class SignupFetch:
  def __init__(self, user_logic: UserLogic, dept_logic: DeptLogic):
    self.user_logic = user_logic
    self.dept_logic = dept_logic
  
  def find_signed_user(self, user_id: str) -> UserResponse:
    # 1. User 도메인 확인 (사용자가 없으면 404 예외 발생)
    user = self.user_logic.retrieve_user_by_id(user_id)
    if not user:
      raise UserNotFoundException(user_id)
    # 2. Dept 도메인 확인 (부서가 없으면 404 예외 발생)
    dept = self.dept_logic.retrieve_dept_by_id(user.dept_id)
    if not dept:
      raise DeptNotFoundException(user.dept_id)
    # 3. User 엔티티에 dept_name 동적 할당 (응답용)
    user.dept_name = dept.name

    # 4. User 엔티티를 Pydantic Response DTO로 변환
    return UserResponse.model_validate(user)
  
  def find_depts(self, dept_name: str | None = None) -> list[DeptResponse]:
    return self.dept_logic.retrieve_depts_by_name_like(dept_name)
  