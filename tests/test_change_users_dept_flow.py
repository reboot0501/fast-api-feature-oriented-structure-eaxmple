import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from domain.dept.dept_entity import Dept
from domain.user.user_entity import User
from feature.organization.organization_flow import OrganizationFlow
from shared.models import IdNameValues
from shared.models.exception import UpdateValueException


class FakeUserLogic:
  def __init__(self, user: User, db: Session):
    self.user = user
    self.db = db
    self.change_calls = []

  def retrieve_user_by_id(self, user_id: str) -> User | None:
    return self.user if user_id == "user-001" else None

  def change_user_dept(self, user: User, new_dept_id: str) -> bool:
    self.change_calls.append((user, new_dept_id))
    return True


class FakeDeptLogic:
  def __init__(self, dept: Dept, db: Session):
    self.dept = dept
    self.db = db

  def retrieve_dept_by_id(self, dept_id: str) -> Dept | None:
    return self.dept if dept_id == "dept-002" else None


def build_flow():
  db = Session(bind=create_engine("sqlite:///:memory:"))
  user = User(
    email="user@example.com",
    name="User",
    password="hashed-password",
    dept_id="dept-001",
  )
  dept = Dept(name="New Department")
  user_logic = FakeUserLogic(user, db)
  dept_logic = FakeDeptLogic(dept, db)
  return OrganizationFlow(user_logic, dept_logic), user_logic, db


def test_change_users_dept_extracts_dept_id_from_id_name_values():
  flow, user_logic, db = build_flow()

  result = flow.change_users_dept([
    IdNameValues.of("user-001", {"dept_id": "dept-002"})
  ])

  assert result == [True]
  assert user_logic.change_calls == [(user_logic.user, "dept-002")]
  db.close()


def test_change_users_dept_rejects_non_dept_id_properties():
  flow, _, db = build_flow()

  with pytest.raises(UpdateValueException):
    flow.change_users_dept([
      IdNameValues.of("user-001", {"name": "Changed User"})
    ])

  db.close()