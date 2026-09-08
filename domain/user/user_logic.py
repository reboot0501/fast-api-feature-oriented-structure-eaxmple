# domain/user/user_logic.py
# 도메인 계층의 비즈니스 로직(Service)을 구현하는 파일입니다.
# 비즈니스 규칙을 처리하고, 데이터베이스 작업은 UserRepository에게 위임합니다.

from app.config.transaction import transactional
from shared.models import OffsetElementList
from shared.models.exception import UserAlreadyExistsException, UserNotFoundException
from shared.utils.hash_helper import hash_password
from shared.utils import PaginationResult
from domain.user.user_repository import UserRepository
from .user_entity import User
from .user_dto import UserCreate, UserUpdate

class UserLogic:
  # UserRepository를 생성자 주입받음
  def __init__(self, user_repo: UserRepository):
    self.repo = user_repo
  
  @transactional
  def register_user(self, user_create: UserCreate) -> User:
    # user_repo는 이미 db를 갖고 있으므로 email만 전달
    db_user = self.repo.get_user_by_email(email=user_create.email)
    if db_user:
        raise UserAlreadyExistsException()

    # Pydantic DTO를 dict로 변환하고 비밀번호만 해싱 값으로 대체하여 언패킹(**)
    user_data = user_create.model_dump()

    # 비밀번호 단방향 암호화
    user_data["password"] = hash_password(user_create.password)

    # 일일이 매핑할 필요 없이 **user_data로 엔티티 자동 생성
    new_user = User(**user_data)
    return self.repo.create_user(new_user)

  @transactional
  def modify_user(self, user_id: str, user_update: UserUpdate) -> User:
    # 수정 대상은 user_id로 고정 조회 (email은 "바꿀 값"일 수도 있어 조회 키로 쓰면
    # 이메일 자체를 변경하려는 요청에서 기존 사용자를 못 찾는 문제가 생긴다)
    db_user = self.repo.get_user_by_id(user_id)
    if not db_user:
        raise UserNotFoundException(user_id)

    # 수정할 필드만 매핑
    user_data = user_update.model_dump(exclude_unset=True)

    # 이메일을 변경하는 경우, 다른 사용자와 중복되지 않는지 확인
    new_email = user_data.get("email")
    if new_email and new_email != db_user.email:
        existing_user = self.repo.get_user_by_email(email=new_email)
        if existing_user:
            raise UserAlreadyExistsException()

    # 만약 비밀번호도 수정하는 경우
    if "password" in user_data:
        user_data["password"] = hash_password(user_data["password"])

    # 변경 사항을 엔티티에 적용
    return self.repo.update_user(db_user, user_data)

  @transactional
  def change_user_dept(self, user: User, new_dept_id: str) -> bool:
    """
    사용자의 소속 부서 변경
    - 대상 사용자와 부서의 존재 여부는 호출 Feature에서 확인한다.
    - 사용자 Entity의 dept_id만 수정하고 결과를 bool로 반환한다.
    """
    update_data = {"dept_id": new_dept_id}
    updated_user = self.repo.update_user(user, update_data)
    return updated_user is not None
    
  def retrieve_user_by_id(self, user_id: str) -> User:
    user = self.repo.get_user_by_id(user_id)
    if not user:
      raise UserNotFoundException(user_id)
    return user

  def retrieve_users_by_dept_id(self, dept_id: str) -> list[User]:
    """
    특정 부서에 소속된 사용자 목록 조회
    :param dept_id: 부서 ID
    :return: 해당 부서에 소속된 사용자 목록 (list[User])
    """
    return self.repo.get_users_by_dept_id(dept_id)

  @transactional
  def remove_user(self, user_id: str) -> bool:
    """
    사용자 삭제
    """
    user = self.repo.get_user_by_id(user_id)
    if not user:
      raise UserNotFoundException(user_id)
    
    # 소프트 삭제 실행 (UserRepository의 remove 메서드 호출)
    return self.repo.delete_user(user)

  def retrieve_all(self) -> list[User]:
    return self.repo.get_all_users()
  
  def retrieve_users_by_name_like(self, name: str) -> list[User]:
    return self.repo.get_users_by_name_like(name)

  def count_users(self, user_name: str | None = None, dept_id: str | None = None) -> int:
    return self.repo.count_users_by_name_like_and_dept_id(user_name, dept_id)

  def retrieve_users_by_name_like_and_dept_id_paginated(
      self, 
      user_name: str | None = None, 
      dept_id: str | None = None, 
      page: int = 1, 
      size: int = 10, 
      order: str = "desc"
    ) -> PaginationResult[User]:
    return self.repo.get_users_paginated_by_name_like_and_dept_id(user_name, dept_id, page, size, order)    