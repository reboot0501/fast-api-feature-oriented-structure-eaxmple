from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from domain.user.user_entity import User
from domain.user.user_logic import UserLogic


class FakeUserRepository:
  def __init__(self, db: Session):
    self.db = db
    self.update_calls = []

  def update_user(self, user: User, update_data: dict) -> User:
    self.update_calls.append((user, update_data))
    for key, value in update_data.items():
      setattr(user, key, value)
    return user


def test_change_user_dept_updates_only_dept_id_and_returns_true():
  db = Session(bind=create_engine("sqlite:///:memory:"))
  repository = FakeUserRepository(db)
  logic = UserLogic(repository)
  user = User(
    email="user@example.com",
    name="User",
    password="hashed-password",
    dept_id="old-dept",
  )
  new_dept_id = "new-dept"

  result = logic.change_user_dept(user, new_dept_id)

  assert result is True
  assert user.dept_id == new_dept_id
  assert repository.update_calls == [(user, {"dept_id": new_dept_id})]
  db.close()