# domain/dept/dept_logic.py

import uuid
from app.config.transaction import transactional
from shared.models import OffsetElementList
from shared.models.exception import DeptAlreadyExistsException
from shared.utils import PaginationResult
from domain.dept.dept_entity import Dept
from domain.dept.dept_dto import DeptCreate
from domain.dept.dept_repository import DeptRepository

class DeptLogic:
  """
  DeptRepository 의존성 주입
  """
  def __init__(self, dept_repository: DeptRepository):
    self.dept_repository = dept_repository

  @transactional
  def register_dept(self, dept_create: DeptCreate) -> Dept:
    """
    부서 생성
    :param dept: 생성할 부서 정보 (Dept)
    :return: 생성된 부서 정보 (Dept)
    """
    if self.dept_repository.get_dept_by_name(dept_create.name):
      raise DeptAlreadyExistsException()

    new_dept = Dept(**dept_create.model_dump())
    return self.dept_repository.create_dept(new_dept)

  def retrieve_depts_by_name_like_paginated(
    self, 
    dept_name: str | None = None, 
    page: int = 1, 
    size: int = 10, 
    order: str = "desc"
  ) -> PaginationResult[Dept]:
    """
    부서 목록 페이징 조회 (부서명 LIKE 검색 및 정렬 방향 지원)
    :param dept_name: 검색할 부서 이름 (None이면 전체 조회)
    :param page: 페이지 번호 (1부터 시작)
    :param size: 페이지당 데이터 개수 (기본 10개)
    :param order: 정렬 방향 ("desc": 최신순, "asc": 오래된순, 기본값 "desc")
    :return: 해당 페이지의 부서 페이징 목록 (OffsetElementList[Dept])
    """
    return self.dept_repository.get_depts_by_name_like_paginated(dept_name, page, size, order)
  
  def retrieve_dept_by_id(self, dept_id: str | uuid.UUID) -> Dept | None:
    """
    부서 ID로 단일 부서 조회
    :param dept_id: 부서 ID
    :return: 해당 부서 정보 (Dept) 또는 None
    """
    return self.dept_repository.get_dept_by_id(dept_id)

  def retrieve_depts_by_ids(self, dept_ids: list[str]) -> list[Dept]:
    return self.dept_repository.get_depts_by_ids(dept_ids)
  
  def count_depts_by_name_like(self, dept_name: str | None = None) -> int:
    """
    전체 부서 건수 조회 (부서명 검색 조건 포함)
    :param dept_name: 검색할 부서명 (None이면 전체 조회)
    :return: 해당 부서의 개수 (int)
    """
    return self.dept_repository.count_depts_by_name_like(dept_name)
  
  @transactional
  def modify_dept(self, dept: Dept, update_data: dict | None = None) -> Dept:
    """
    부서 정보 수정
    :param dept: 수정할 부서 객체
    :param update_data: 수정할 데이터 딕셔너리
    :return: 수정된 부서 정보 (Dept)
    """
    return self.dept_repository.update_dept(dept, update_data)
  
  @transactional
  def remove_dept(self, dept_or_id: str | Dept) -> bool:
    """
    부서 삭제
    :param dept_or_id: 삭제할 부서 객체 또는 부서 ID
    """
    # Repository의 삭제 결과를 상위 Feature와 API 응답까지 그대로 전달한다.
    return self.dept_repository.delete_dept(dept_or_id)

  def retrieve_depts_by_name_like(self, dept_name: str | None = None) -> list[Dept]:
    """
    부서명 LIKE 검색 (전체 결과 반환)
    :param dept_name: 검색할 부서명 (None이면 전체 조회)
    :return: 해당 부서의 목록 (list[Dept])
    """
    return self.dept_repository.get_depts_by_name_like(dept_name)