import pytest

from domain.dept.dept_dto import DeptCreate
from domain.dept.dept_entity import Dept
from domain.dept.dept_logic import DeptLogic
from shared.models.exception import DeptAlreadyExistsException


class FakeDeptRepository:
  def __init__(self, existing_dept: Dept | None = None):
    self.existing_dept = existing_dept
    self.created_dept = None

  def get_dept_by_name(self, name: str) -> Dept | None:
    if self.existing_dept and self.existing_dept.name == name:
      return self.existing_dept
    return None

  def create_dept(self, dept: Dept) -> Dept:
    self.created_dept = dept
    return dept


def test_register_dept_converts_create_dto_to_entity():
  repository = FakeDeptRepository()
  logic = DeptLogic(repository)

  result = logic.register_dept(DeptCreate(name="Platform", desc="Core team"))

  assert isinstance(repository.created_dept, Dept)
  assert repository.created_dept.name == "Platform"
  assert repository.created_dept.desc == "Core team"
  assert result is repository.created_dept


def test_register_dept_rejects_duplicate_name():
  existing_dept = Dept(name="Platform")
  repository = FakeDeptRepository(existing_dept)
  logic = DeptLogic(repository)

  with pytest.raises(DeptAlreadyExistsException):
    logic.register_dept(DeptCreate(name="Platform"))

  assert repository.created_dept is None