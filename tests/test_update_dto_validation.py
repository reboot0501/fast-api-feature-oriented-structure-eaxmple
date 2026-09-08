import pytest

from domain.dept.dept_dto import DeptUpdate
from domain.user.user_dto import UserUpdate
from shared.models.exception import UpdateValueException
from shared.utils import AtLeastOneValueMixin


@pytest.mark.parametrize("update_type", [UserUpdate, DeptUpdate])
def test_update_dto_requires_at_least_one_value(update_type):
  with pytest.raises(UpdateValueException):
    update_type()


@pytest.mark.parametrize("update_type", [UserUpdate, DeptUpdate])
def test_update_dto_rejects_explicit_null_values(update_type):
  with pytest.raises(UpdateValueException):
    update_type.model_validate({"name": None})


def test_update_dto_accepts_one_value():
  assert UserUpdate(name="User").name == "User"
  assert DeptUpdate(name="Platform").name == "Platform"


def test_mixin_is_publicly_exported():
  assert AtLeastOneValueMixin.__name__ == "AtLeastOneValueMixin"