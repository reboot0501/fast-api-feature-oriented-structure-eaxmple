import shared.models
import shared.utils

from shared.models import (
  DeptAlreadyExistsException,
  DeptNotFoundException,
  UpdateValueException,
  UserAlreadyExistsException,
  UserNotFoundException,
)


def test_exceptions_are_publicly_exported_from_shared_models():
  assert shared.models.UserNotFoundException is UserNotFoundException
  assert shared.models.UserAlreadyExistsException is UserAlreadyExistsException
  assert shared.models.DeptNotFoundException is DeptNotFoundException
  assert shared.models.DeptAlreadyExistsException is DeptAlreadyExistsException
  assert shared.models.UpdateValueException is UpdateValueException


def test_exceptions_are_not_reexported_from_shared_utils():
  assert not hasattr(shared.utils, "UserNotFoundException")
  assert not hasattr(shared.utils, "UserAlreadyExistsException")
  assert not hasattr(shared.utils, "DeptNotFoundException")
  assert not hasattr(shared.utils, "DeptAlreadyExistsException")
  assert not hasattr(shared.utils, "UpdateValueException")