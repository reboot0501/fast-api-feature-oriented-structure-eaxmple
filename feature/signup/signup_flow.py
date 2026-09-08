# feature/signup/signup_flow.py

from shared.models.exception import DeptNotFoundException
from domain.user import UserResponse
from domain.user import UserCreate
from domain.user import UserUpdate
from app.config.transaction import transactional
from domain.dept import DeptLogic
from domain.user import UserLogic
class SignupFlow:

  def __init__(self, user_logic: UserLogic, dept_logic: DeptLogic):
    self.user_logic = user_logic
    self.dept_logic = dept_logic

  @transactional
  def signup(self, user_create: UserCreate) -> UserResponse:
    dept = self.dept_logic.retrieve_dept_by_id(user_create.dept_id)
    if not dept:
      raise DeptNotFoundException(user_create.dept_id)
    # 1. 사용자 생성 (UserLogic의 메서드 호출)
    user = self.user_logic.register_user(user_create)
    # 2. ✅ 엔티티 객체에 dept_name 속성을 동적으로 세팅
    user.dept_name = dept.name
    # 3. model_validate가 user.dept_name까지 함께 매핑하여 반환
    return UserResponse.model_validate(user)

  @transactional
  def modify_user(self, user_id: str, user_update: UserUpdate) -> UserResponse:
    # 1. dept_id를 변경하는 요청이면, 실제 DB 반영 전에 부서 존재부터 확인 (signup과 동일 패턴)
    if user_update.dept_id:
      new_dept = self.dept_logic.retrieve_dept_by_id(user_update.dept_id)
      if not new_dept:
        raise DeptNotFoundException(user_update.dept_id)
    # 2. 사용자 정보 수정 (UserLogic의 메서드 호출, user_id로 대상 고정)
    user = self.user_logic.modify_user(user_id, user_update)
    # 3. 응답용 dept_name 세팅 (dept_id 미변경 시에도 현재 소속 부서명을 채워준다)
    dept = self.dept_logic.retrieve_dept_by_id(user.dept_id)
    if not dept:
      raise DeptNotFoundException(user.dept_id)
    user.dept_name = dept.name
    return UserResponse.model_validate(user)
