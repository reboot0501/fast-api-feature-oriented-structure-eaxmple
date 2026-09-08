from domain.dept.dept_entity import Dept
from domain.dept.dept_logic import DeptLogic
from domain.dept.dept_repository import DeptRepository
from domain.user.user_entity import User
from domain.user.user_repository import UserRepository


class FakeSession:
  def __init__(self, entities=None):
    self.entities = entities or {}
    self.deleted = []
    self.flush_count = 0

  def get(self, entity_type, entity_id):
    return self.entities.get((entity_type, entity_id))

  def delete(self, entity):
    self.deleted.append(entity)

  def flush(self):
    self.flush_count += 1


def test_delete_dept_returns_true_when_entity_is_deleted():
  db = FakeSession()
  dept = Dept(name="Platform")

  result = DeptRepository(db).delete_dept(dept)

  assert result is True
  assert db.deleted == [dept]
  assert db.flush_count == 1


def test_delete_dept_returns_false_when_entity_does_not_exist():
  result = DeptRepository(FakeSession()).delete_dept("missing-dept")

  assert result is False


def test_delete_user_returns_true_when_entity_is_deleted():
  db = FakeSession()
  user = User(
    email="user@example.com",
    name="User",
    password="hashed-password",
    dept_id="dept-id",
  )

  result = UserRepository(db).delete_user(user)

  assert result is True
  assert db.deleted == [user]
  assert db.flush_count == 1


def test_delete_user_returns_false_when_entity_does_not_exist():
  result = UserRepository(FakeSession()).delete_user("missing-user")

  assert result is False


class FakeDeptRepository:
  def delete_dept(self, dept_or_id):
    return True


def test_dept_logic_returns_repository_delete_result():
  result = DeptLogic(FakeDeptRepository()).remove_dept("dept-id")

  assert result is True