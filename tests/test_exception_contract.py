import pytest

from shared.models.exception import (
  DeptAlreadyExistsException,
  DeptNotFoundException,
  UpdateValueException,
  UserAlreadyExistsException,
  UserNotFoundException,
)


@pytest.mark.parametrize(
  ("exception_type", "identifier", "status_code", "detail"),
  [
    (UserNotFoundException, "user-id", 404, "user-id"),
    (DeptNotFoundException, "dept-id", 404, "dept-id"),
  ],
)
def test_not_found_exception_accepts_identifier(
  exception_type,
  identifier,
  status_code,
  detail,
):
  exception = exception_type(identifier)

  assert exception.status_code == status_code
  assert detail in exception.detail


def test_existing_exception_contracts_keep_their_http_statuses():
  assert UserAlreadyExistsException().status_code == 400
  assert DeptAlreadyExistsException().status_code == 400
  assert UpdateValueException().status_code == 422