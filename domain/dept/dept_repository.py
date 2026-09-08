# domain/dept/dept_repository.py

import uuid
from domain.dept.dept_entity import Dept
from sqlalchemy.orm import Session
from shared.utils import PaginationResult, paginate, to_uuid, to_uuid_or_none
class DeptRepository:
  # 생성자 주입(Constructor Dependency Injection)을 통해 외부에서 DB 세션을 전달받아 보관하는 로직
  def __init__(self, db: Session):
    self.db = db

  def create_dept(self, dept: Dept) -> Dept:
    self.db.add(dept)
    self.db.flush()
    self.db.refresh(dept)
    return dept

  def get_depts_by_name_like_paginated(
    self, 
    dept_name: str | None = None, 
    page: int = 1, 
    size: int = 10, 
    order: str = "desc"
  ) -> PaginationResult[Dept]:
    """
    부서 목록 페이징 조회 (부서명 LIKE 검색 및 정렬 방향 지원)
    :param dept_name: 검색할 사용자 이름 (None이면 전체 조회)
    :param page: 페이지 번호 (1부터 시작)
    :param size: 페이지당 데이터 개수 (기본 10개)
    :param order: 정렬 방향 ("desc": 최신순, "asc": 오래된순, 기본값 "desc")
    :return: 해당 페이지의 부서 목록 (list[Dept])
    """
    query = self.db.query(Dept)

    # dept_name이 전달된 경우 LIKE 조건 추가
    if dept_name:
      query = query.filter(Dept.name.like(f"%{dept_name}%"))

    return paginate(
      query=query,
      order_column=Dept.name,
      page=page,
      size=size,
      order=order,
    )

  def get_depts_by_ids(self, dept_ids: list[str]) -> list[Dept]:
    return self.db.query(Dept).filter(Dept.id.in_([to_uuid(d) for d in dept_ids])).all()

  def get_dept_by_id(self, dept_id: str | uuid.UUID) -> Dept | None:
    dept_uuid = to_uuid_or_none(dept_id)
    if dept_uuid is None:
      # 형식이 잘못된 id는 어떤 행과도 매칭될 수 없으므로 "존재하지 않음"으로 처리
      return None
    return self.db.get(Dept, dept_uuid)

  def get_dept_by_name(self, name: str) -> Dept | None:
    return self.db.query(Dept).filter(Dept.name == name).first()
  

  def count_depts_by_name_like(self, dept_name: str | None = None) -> int:
    """
    전체 부서 건수 조회 (부서명 검색 조건 포함)
    :param dept_name: 검색할 부서명 (None이면 전체 조회)
    :return: 해당 부서의 개수 (int)
    """
    query = self.db.query(Dept)
    if dept_name:
      query = query.filter(Dept.name.like(f"%{dept_name}%"))
    return query.count()

  def update_dept(self, dept: Dept, update_data: dict | None = None) -> Dept:
    if update_data:
      for key, value in update_data.items():
        setattr(dept, key, value)
    self.db.flush()  # 변경 사항 DB 반영 (커밋은 @transactional이 수행)
    self.db.refresh(dept)
    return dept

  def delete_dept(self, dept_or_id: str | Dept) -> bool:
    if isinstance(dept_or_id, Dept):
      dept = dept_or_id
    else:
      dept_uuid = to_uuid_or_none(dept_or_id)
      dept = self.db.get(Dept, dept_uuid) if dept_uuid is not None else None
    if dept:
      self.db.delete(dept)
      self.db.flush()  # 삭제 상태 DB 반영 (커밋은 @transactional이 수행)
      # 실제 삭제 예약과 flush가 완료된 경우에만 성공으로 응답한다.
      return True
    # 대상이 없으면 삭제 작업이 수행되지 않았음을 명시한다.
    return False