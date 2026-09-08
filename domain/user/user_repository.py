# domain/user/user_repository.py

import uuid
from sqlalchemy.orm import Session
from domain.user.user_entity import User
from shared.utils.hash_helper import hash_password
from shared.utils import PaginationResult, paginate, to_uuid, to_uuid_or_none

class UserRepository:
  # 생성자 주입(Constructor Dependency Injection)을 통해 외부에서 DB 세션을 전달받아 보관하는 로직
  def __init__(self, db: Session):
    self.db = db
  
  def create_user(self, user: User) -> User:
    self.db.add(user)
    self.db.flush()  # DB에 전송하여 ID 및 생성일자 확정 (커밋은 @transactional이 수행)
    self.db.refresh(user)
    return user

  def get_user_by_email(self, email: str) -> User | None:
    return self.db.query(User).filter(User.email == email).first()
  
  def get_user_by_id(self, user_id: str | uuid.UUID) -> User | None:
    user_uuid = to_uuid_or_none(user_id)
    if user_uuid is None:
      # 형식이 잘못된 id는 어떤 행과도 매칭될 수 없으므로 "존재하지 않음"으로 처리
      return None
    return self.db.get(User, user_uuid)

  def get_users_by_dept_id(self, dept_id: str) -> list[User]:
    return self.db.query(User).filter(User.dept_id == dept_id).all()
  
  def get_all_users(self) -> list[User]:
    return self.db.query(User).all()

  def update_user(self, user: User, update_data: dict | None = None) -> User:
    if update_data:
      for key, value in update_data.items():
        setattr(user, key, value)
    self.db.flush()  # 변경 사항 DB 반영 (커밋은 @transactional이 수행)
    self.db.refresh(user)
    return user

  def delete_user(self, user_or_id: str | User) -> bool:
    if isinstance(user_or_id, User):
      user = user_or_id
    else:
      user_uuid = to_uuid_or_none(user_or_id)
      user = self.db.get(User, user_uuid) if user_uuid is not None else None
    if user:
      self.db.delete(user)
      self.db.flush()  # 삭제 상태 DB 반영 (커밋은 @transactional이 수행)
      # 실제 삭제 예약과 flush가 완료된 경우에만 성공으로 응답한다.
      return True
    # 대상이 없으면 삭제 작업이 수행되지 않았음을 명시한다.
    return False
  
  def get_users_by_name_like(self, name: str) -> list[User]:
    return self.db.query(User).filter(User.name.like(f"%{name}%")).all()

  def count_users_by_name_like_and_dept_id(self, user_name: str | None = None, dept_id: str | None = None) -> int:
    """전체 사용자 총 건수 조회 (이름 검색 조건 포함)"""
    query = self.db.query(User) # ① 아직 DB에 아무 요청도 안 함 (SQL 문장 조립 준비)
    if user_name:
      query = query.filter(User.name.like(f"%{user_name}%")) # ② WHERE 조건 추가 (아직도 실행 안 됨)
    if dept_id:
      query = query.filter(User.dept_id == dept_id)
    return query.count() # ③ count() 호출 순간에 실제 DB 쿼리(SELECT COUNT(*)...)가 실행됨!

  def get_users_paginated_by_name_like_and_dept_id(
    self, 
    user_name: str | None = None,
    dept_id: str | None = None,
    page: int = 1, 
    size: int = 10, 
    order: str = "desc"
  ) -> PaginationResult[User]:
    """
    사용자 목록 페이징 조회 (이름 LIKE 검색 및 정렬 방향 지원)
    :param user_name: 검색할 사용자 이름 (None이면 전체 조회)
    :param page: 페이지 번호 (1부터 시작)
    :param size: 페이지당 데이터 개수 (기본 10개)
    :param order: 정렬 방향 ("desc": 최신순, "asc": 오래된순, 기본값 "desc")
    :return: 해당 페이지의 사용자 목록 (list[User])
    """
    query = self.db.query(User)
    
    # user_name이 전달된 경우 LIKE 조건 추가
    if user_name:
      query = query.filter(User.name.like(f"%{user_name}%"))
    if dept_id:
      query = query.filter(User.dept_id == dept_id)
    return paginate(
      query=query,
      order_column=User.name,
      page=page,
      size=size,
      order=order,
    )
